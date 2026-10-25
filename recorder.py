"""ReplayCore capture engine. Python standard library + external FFmpeg only."""

from __future__ import annotations

import math
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SEGMENT_SECONDS = 2


@dataclass(frozen=True)
class Settings:
    duration: int = 30
    fps: int = 30
    resolution: str = "720p"
    encoder: str = "Otomatik"
    audio_device: str = ""


def app_directory() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def locate_ffmpeg() -> str | None:
    """Locate a side-by-side or PyInstaller-bundled FFmpeg executable."""
    import sys

    roots = [app_directory()]
    # In PyInstaller --onefile, extra binaries unpack under sys._MEIPASS.
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        roots.append(Path(bundle_dir))
    for root in roots:
        for name in ("ffmpeg.exe", "ffmpeg"):
            candidate = root / name
            if candidate.is_file():
                return str(candidate)
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def process_options() -> dict:
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def installed_encoders(ffmpeg: str) -> set[str]:
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=12,
            **process_options(),
        )
        return set(re.findall(r"\b(?:h264_nvenc|h264_amf|libx264)\b", proc.stdout))
    except (OSError, subprocess.TimeoutExpired):
        return set()


def encoder_candidates(mode: str, available: set[str]) -> list[str]:
    lookup = {
        "Otomatik": ["h264_nvenc", "h264_amf", "libx264"],
        "NVIDIA NVENC": ["h264_nvenc", "libx264"],
        "AMD AMF": ["h264_amf", "libx264"],
        "CPU x264": ["libx264"],
    }
    choices = lookup.get(mode, lookup["Otomatik"])
    # FFmpeg may list a hardware encoder even when the machine does not support it.
    return [encoder for encoder in choices if encoder in available]


def capture_command(ffmpeg: str, settings: Settings, codec: str, session: Path) -> list[str]:
    args = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "warning",
        "-thread_queue_size", "512", "-f", "gdigrab",
        "-framerate", str(settings.fps), "-draw_mouse", "1", "-i", "desktop",
    ]
    if settings.audio_device.strip():
        args += [
            "-thread_queue_size", "512", "-f", "dshow",
            "-i", "audio=" + settings.audio_device.strip(),
        ]
    args += ["-map", "0:v:0"]
    if settings.audio_device.strip():
        args += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "160k"]
    else:
        args += ["-an"]

    # gdigrab captures the desktop with GDI, without requiring any GPU encoder.
    filters = ["pad=ceil(iw/2)*2:ceil(ih/2)*2"]
    if settings.resolution != "Orijinal":
        height = int(settings.resolution.removesuffix("p"))
        filters.insert(0, f"scale=-2:{height}")
    filters.append("format=yuv420p")
    args += ["-vf", ",".join(filters)]
    args += [
        "-c:v", codec, "-pix_fmt", "yuv420p",
        "-g", str(settings.fps * SEGMENT_SECONDS),
        "-bf", "0", "-force_key_frames", "expr:gte(t,n_forced*2)",
    ]
    if codec == "libx264":
        args += ["-preset", "ultrafast", "-crf", "25", "-tune", "zerolatency"]
    else:
        bitrate = "6500k" if settings.resolution in ("1080p", "Orijinal") else "3500k"
        args += ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", "10000k"]
    args += [
        "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
        "-segment_format", "mpegts", "-reset_timestamps", "1",
        str(session / "part_%06d.ts"),
    ]
    return args


def segment_files(session: Path) -> list[Path]:
    return sorted(session.glob("part_*.ts"))


def prune_segments(session: Path, duration: int) -> None:
    """Keep a short rolling disk buffer and an extra margin for keyframes."""
    segments = segment_files(session)
    max_segments = math.ceil(duration / SEGMENT_SECONDS) + 5
    # Never delete the newest two files: FFmpeg may still be using them.
    for segment in segments[: max(0, len(segments) - max_segments)]:
        try:
            segment.unlink()
        except OSError:
            pass


def snapshot_segments(session: Path, staging: Path, duration: int) -> list[Path]:
    """Copy the most recent chunks while recording continues.

    The newest MPEG-TS segment may still be open. A partial copy is often
    remuxable, but if Windows has it locked, omit it rather than losing the save.
    """
    files = segment_files(session)
    count = math.ceil(duration / SEGMENT_SECONDS) + 1
    captured = []
    for source in files[-count:]:
        if not source.is_file() or source.stat().st_size < 1024:
            continue
        target = staging / f"chunk_{len(captured):04d}.ts"
        try:
            shutil.copyfile(source, target)
            if target.stat().st_size >= 1024:
                captured.append(target)
            else:
                target.unlink(missing_ok=True)
        except OSError:
            target.unlink(missing_ok=True)
    return captured


def remux_to_mp4(ffmpeg: str, clips: list[Path], destination: Path) -> None:
    """Combine independent 2-second TS chunks without re-encoding."""
    if not clips:
        raise RuntimeError("Henuz kaydedilecek goruntu bulunamadi.")
    concat_path = clips[0].parent / "concat.txt"
    # Staging names contain only predictable ASCII, and are resolved locally.
    concat_path.write_text(
        "".join(f"file '{item.name}'\n" for item in clips), encoding="utf-8"
    )
    dest_tmp = destination.with_suffix(".partial.mp4")
    try:
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(concat_path),
                "-map", "0:v:0", "-map", "0:a?", "-c", "copy",
                "-movflags", "+faststart", str(dest_tmp),
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, errors="replace", timeout=180, **process_options(),
        )
        if result.returncode != 0 or not dest_tmp.is_file() or dest_tmp.stat().st_size < 1024:
            message = (result.stderr or "FFmpeg cikti olusturamadi.")[-900:]
            raise RuntimeError("MP4 birlestirme hatasi: " + message)
        dest_tmp.replace(destination)
    finally:
        dest_tmp.unlink(missing_ok=True)


def audio_devices(ffmpeg: str) -> list[str]:
    """DirectShow recording inputs, e.g. Stereo Mix or a microphone."""
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, errors="replace", timeout=12,
            **process_options(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    found, in_audio_section = [], False
    for line in result.stderr.splitlines():
        if "DirectShow audio devices" in line:
            in_audio_section = True
            continue
        if "DirectShow video devices" in line:
            in_audio_section = False
            continue
        if in_audio_section and '"' in line and "Alternative name" not in line:
            match = re.search(r'"([^\"]+)"', line)
            if match and match.group(1) not in found:
                found.append(match.group(1))
    return found


class RecorderEngine:
    def __init__(self, event_callback: Callable[[str, object], None]) -> None:
        self.on_event = event_callback
        self.ffmpeg = locate_ffmpeg()
        self.cache = Path(tempfile.gettempdir()) / "ReplayCore"
        self.cache.mkdir(parents=True, exist_ok=True)
        self._remove_old_sessions()
        self.session: Path | None = None
        self.process: subprocess.Popen | None = None
        self.settings = Settings()
        self.phase = "idle"
        self.stop_signal = threading.Event()
        self.buffer_lock = threading.Lock()
        self.save_lock = threading.Lock()
        self.thread: threading.Thread | None = None

    def _remove_old_sessions(self) -> None:
        # Only remove ReplayCore's own expired session folders.
        for folder in self.cache.glob("session_*"):
            try:
                if folder.is_dir() and time.time() - folder.stat().st_mtime > 48 * 3600:
                    shutil.rmtree(folder, ignore_errors=True)
            except OSError:
                pass

    def emit(self, event: str, data: object = None) -> None:
        self.on_event(event, data)

    def start(self, settings: Settings) -> bool:
        if self.phase != "idle":
            return False
        self.ffmpeg = locate_ffmpeg()
        if not self.ffmpeg:
            self.emit("error", "ffmpeg.exe bulunamadi. Once KUR_FFMPEG.bat dosyasini calistir.")
            return False
        self.settings = settings
        self.stop_signal.clear()
        self.session = self.cache / ("session_" + uuid.uuid4().hex)
        self.session.mkdir(parents=True, exist_ok=True)
        self.phase = "starting"
        self.thread = threading.Thread(target=self._run_capture, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        if self.phase in ("starting", "recording"):
            self.phase = "stopping"
            self.stop_signal.set()
            self.emit("stopping", None)

    def shutdown(self) -> None:
        """Ensure FFmpeg is not left recording after the GUI exits."""
        self.stop_signal.set()
        if self.process is not None:
            self._stop_process(self.process)
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=3)

    @staticmethod
    def _stop_process(process: subprocess.Popen) -> None:
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                except OSError:
                    pass

    def _run_capture(self) -> None:
        assert self.ffmpeg and self.session
        reason = "Kayıt motoru başlatılamadı."
        try:
            supported = installed_encoders(self.ffmpeg)
            choices = encoder_candidates(self.settings.encoder, supported)
            if not choices:
                raise RuntimeError("Bu FFmpeg surumunde uygun H.264 kodlayici yok (libx264 gerekli).")
            for codec in choices:
                if self.stop_signal.is_set():
                    break
                self.emit("trying", codec)
                for old in segment_files(self.session):
                    old.unlink(missing_ok=True)
                log_path = self.session / (codec + ".log")
                with log_path.open("w", encoding="utf-8", errors="replace") as log:
                    command = capture_command(self.ffmpeg, self.settings, codec, self.session)
                    try:
                        process = subprocess.Popen(
                            command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=log, **process_options(),
                        )
                    except OSError as exc:
                        reason = str(exc)
                        continue
                    self.process = process
                    started_at = time.monotonic()
                    ready = False
                    while not self.stop_signal.is_set() and time.monotonic() - started_at < 8:
                        if process.poll() is not None:
                            break
                        if len(segment_files(self.session)) >= 2:
                            ready = True
                            break
                        self.stop_signal.wait(0.2)
                    if not ready:
                        self._stop_process(process)
                        self.process = None
                        if log_path.exists():
                            reason = (log_path.read_text(encoding="utf-8", errors="replace")[-900:] or reason)
                        continue
                    self.phase = "recording"
                    self.emit("started", codec)
                    while not self.stop_signal.wait(0.6):
                        if process.poll() is not None:
                            reason = "FFmpeg beklenmedik sekilde kapandi. " + log_path.read_text(
                                encoding="utf-8", errors="replace"
                            )[-600:]
                            self.emit("error", reason)
                            break
                        with self.buffer_lock:
                            prune_segments(self.session, self.settings.duration)
                    self._stop_process(process)
                    self.process = None
                    # A started encoder will not silently switch while recording.
                    break
                if ready or self.stop_signal.is_set():
                    break
            else:
                if not self.stop_signal.is_set():
                    self.emit("error", "Kayit baslatilamadi. FFmpeg hata ozeti:\n" + reason)
        except Exception as exc:
            self.emit("error", str(exc))
        finally:
            if self.process is not None:
                self._stop_process(self.process)
                self.process = None
            self.phase = "idle"
            self.emit("stopped", None)

    def save(self, destination_folder: Path) -> bool:
        if self.phase != "recording" or not self.session or not self.ffmpeg:
            self.emit("hint", "Once kaydi baslat ve birkac saniye bekle.")
            return False
        if not self.save_lock.acquire(blocking=False):
            self.emit("hint", "Onceki klip henuz kaydediliyor.")
            return False
        # Bind the session to this save, even if a new capture starts meanwhile.
        threading.Thread(
            target=self._run_save,
            args=(destination_folder, self.session, self.ffmpeg, self.settings.duration),
            daemon=True,
        ).start()
        return True

    def _run_save(self, destination_folder: Path, session: Path, ffmpeg: str, duration: int) -> None:
        staging = Path(tempfile.mkdtemp(prefix="export_", dir=self.cache))
        try:
            self.emit("saving", None)
            with self.buffer_lock:
                clips = snapshot_segments(session, staging, duration)
            if not clips:
                raise RuntimeError("Kayit henuz yeterince ilerlemedi, birkac saniye sonra tekrar dene.")
            destination_folder.mkdir(parents=True, exist_ok=True)
            now = time.strftime("%Y-%m-%d_%H-%M-%S")
            target = destination_folder / f"ReplayCore_{now}_{uuid.uuid4().hex[:4]}.mp4"
            try:
                remux_to_mp4(ffmpeg, clips, target)
            except RuntimeError:
                # A live TS segment may have an incomplete trailing packet.
                # Retry excluding only that youngest segment.
                if len(clips) < 2:
                    raise
                remux_to_mp4(ffmpeg, clips[:-1], target)
            self.emit("saved", str(target))
        except Exception as exc:
            self.emit("save_error", str(exc))
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            self.save_lock.release()
