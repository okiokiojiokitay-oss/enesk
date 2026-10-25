"""Cross-platform tests for the FFmpeg rolling-buffer and remux logic."""
import shutil
import subprocess
import tempfile
import sys
from unittest import mock
import unittest
from pathlib import Path
from recorder import (
    Settings, capture_command, encoder_candidates, prune_segments, locate_ffmpeg,
    remux_to_mp4, segment_files, snapshot_segments,
)


class CoreTests(unittest.TestCase):
    def test_ffmpeg_path_in_onefile_bundle(self):
        # PyInstaller unpacks --add-binary into sys._MEIPASS.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "unpacked"
            bundle.mkdir()
            (bundle / "ffmpeg.exe").write_bytes(b"fake")
            with mock.patch.object(sys, "frozen", True, create=True), \
                 mock.patch.object(sys, "executable", str(root / "ReplayCore.exe")), \
                 mock.patch.object(sys, "_MEIPASS", str(bundle), create=True):
                self.assertEqual(locate_ffmpeg(), str(bundle / "ffmpeg.exe"))

    def test_encoder_fallback_order(self):
        available = {"h264_nvenc", "h264_amf", "libx264"}
        self.assertEqual(encoder_candidates("Otomatik", available),
                         ["h264_nvenc", "h264_amf", "libx264"])
        self.assertEqual(encoder_candidates("AMD AMF", {"libx264"}), ["libx264"])
        self.assertEqual(encoder_candidates("CPU x264", available), ["libx264"])

    def test_capture_command_options(self):
        args = capture_command("ffmpeg", Settings(30, 30, "480p", "CPU x264", ""),
                               "libx264", Path("C:/tmp/record"))
        self.assertIn("gdigrab", args)
        self.assertIn("scale=-2:480,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p", args)
        self.assertIn("ultrafast", args)
        self.assertIn("-force_key_frames", args)
        self.assertIn("-reset_timestamps", args)
        self.assertNotIn("dshow", args)
        args = capture_command("ffmpeg", Settings(audio_device="Stereo Mix"),
                               "h264_amf", Path("C:/tmp/record"))
        self.assertIn("dshow", args)
        self.assertIn("audio=Stereo Mix", args)
        self.assertIn("-c:a", args)

    def test_prune(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for i in range(30):
                (folder / f"part_{i:06d}.ts").write_bytes(b"x" * 2048)
            prune_segments(folder, 15)
            remaining = segment_files(folder)
            self.assertEqual(len(remaining), 13)  # ceil(15/2)+5
            self.assertEqual(remaining[0].name, "part_000017.ts")

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg not installed")
    def test_ffmpeg_segments_can_be_saved_to_mp4(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            session, staging = folder / "session", folder / "export"
            session.mkdir()
            staging.mkdir()
            create = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
                "-t", "7", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-g", "60", "-bf", "0",
                "-force_key_frames", "expr:gte(t,n_forced*2)",
                "-f", "segment", "-segment_time", "2",
                "-segment_format", "mpegts", "-reset_timestamps", "1",
                str(session / "part_%06d.ts"),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(create.returncode, 0, create.stderr)
            self.assertGreaterEqual(len(segment_files(session)), 3)
            clips = snapshot_segments(session, staging, 6)
            self.assertGreaterEqual(len(clips), 3)
            output = folder / "replay.mp4"
            remux_to_mp4("ffmpeg", clips, output)
            self.assertGreater(output.stat().st_size, 10_000)
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(output)
            ], capture_output=True, text=True, timeout=15)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertGreater(float(probe.stdout), 3.0)


if __name__ == "__main__":
    unittest.main()
