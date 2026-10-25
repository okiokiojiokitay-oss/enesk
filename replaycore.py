"""ReplayCore: low-overhead rolling instant replay MVP for Windows."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from hotkeys import Hotkeys
from recorder import RecorderEngine, Settings, audio_devices, locate_ffmpeg

DARK = "#0C111B"
PANEL = "#151E2D"
PANEL2 = "#1D2A3C"
FG = "#F0F5FB"
MUTED = "#99A9C1"
CYAN = "#4DDCFA"
GREEN = "#51D4A6"
RED = "#FB7688"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ReplayCore | Anında Yeniden Oynatma")
        self.root.geometry("666x652")
        self.root.resizable(False, False)
        self.root.configure(bg=DARK)
        self.events: queue.Queue = queue.Queue()
        self.engine = RecorderEngine(lambda event, data: self.events.put((event, data)))
        self.hotkeys = Hotkeys(self.events)
        self.hotkeys.start()
        self.state = "idle"
        self.output_folder = Path.home() / "Videos" / "ReplayCore"
        self.selected_audio = tk.StringVar(value="Ses yok")
        self.selected_duration = tk.StringVar(value="30")
        self.selected_fps = tk.StringVar(value="30")
        self.selected_resolution = tk.StringVar(value="720p")
        self.selected_encoder = tk.StringVar(value="Otomatik")
        self._style()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(100, self._pump_events)

    def _style(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("Settings.TCombobox", padding=7, font=("Segoe UI", 11),
                    fieldbackground=PANEL2, background=PANEL2, foreground=FG,
                    borderwidth=0, arrowsize=16)
        s.map("Settings.TCombobox", fieldbackground=[("readonly", PANEL2)],
              foreground=[("readonly", FG)], selectbackground=[("readonly", PANEL2)],
              selectforeground=[("readonly", FG)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL2)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#264965")

    def _label(self, master, text, size=11, color=FG, bold=False, **opts):
        return tk.Label(master, text=text, bg=master.cget("bg"), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", **opts)

    def _build(self):
        head = tk.Frame(self.root, bg=DARK)
        head.pack(fill="x", padx=30, pady=(24, 8))
        self._label(head, "●  REPLAYCORE", 23, CYAN, True).pack(anchor="w")
        self._label(head, "Ekran kartından bağımsız anında replay", 10, MUTED).pack(anchor="w", pady=(3, 0))

        status_bar = tk.Frame(self.root, bg=PANEL, padx=16, pady=12)
        status_bar.pack(fill="x", padx=29, pady=(14, 13))
        self.status_head = self._label(status_bar, "○  Kayıt beklemede", 13, MUTED, True)
        self.status_head.pack(anchor="w")
        self.status_sub = self._label(status_bar, "Ekran kaydı başlayınca son saniyeler otomatik tutulur.", 9, MUTED)
        self.status_sub.pack(anchor="w", pady=(4, 0))

        settings_panel = tk.Frame(self.root, bg=PANEL, padx=16, pady=13)
        settings_panel.pack(fill="x", padx=29)
        self._label(settings_panel, "KAYIT AYARLARI", 11, FG, True).pack(anchor="w", pady=(0, 10))

        row1 = tk.Frame(settings_panel, bg=PANEL)
        row1.pack(fill="x", pady=(0, 10))
        self._make_combo(row1, "Tekrar süresi", self.selected_duration, ["15", "30", "60", "120"], 0)
        self._make_combo(row1, "Görüntü kalitesi", self.selected_resolution,
                         ["480p", "720p", "1080p", "Orijinal"], 1)

        row2 = tk.Frame(settings_panel, bg=PANEL)
        row2.pack(fill="x", pady=(0, 10))
        self._make_combo(row2, "FPS", self.selected_fps, ["15", "30", "60"], 0)
        self._make_combo(row2, "Video kodlayıcı", self.selected_encoder,
                         ["Otomatik", "NVIDIA NVENC", "AMD AMF", "CPU x264"], 1)

        audio_row = tk.Frame(settings_panel, bg=PANEL)
        audio_row.pack(fill="x")
        self._label(audio_row, "Ses kaynağı (isteğe bağlı)", 10, MUTED).pack(anchor="w")
        controls = tk.Frame(audio_row, bg=PANEL)
        controls.pack(fill="x", pady=(5, 0))
        self.audio_combo = ttk.Combobox(controls, textvariable=self.selected_audio,
                                       values=["Ses yok"], style="Settings.TCombobox")
        self.audio_combo.pack(side="left", fill="x", expand=True)
        self.scan_button = tk.Button(controls, text="Aygıtları tara", cursor="hand2",
                                     command=self._scan_audio, bg=PANEL2, fg=FG,
                                     relief="flat", activebackground="#29435C",
                                     activeforeground=FG, padx=12, pady=7)
        self.scan_button.pack(side="left", padx=(9, 0))
        self._label(settings_panel, "Oyun sesi için Stereo Mix veya sanal ses aygıtı gerekir.",
                    9, MUTED).pack(anchor="w", pady=(7, 0))

        actions = tk.Frame(self.root, bg=DARK)
        actions.pack(fill="x", padx=29, pady=(19, 0))
        self.record_button = tk.Button(actions, text="▶  KAYDI BAŞLAT", command=self._toggle,
                                       fg=DARK, bg=CYAN, activeforeground=DARK,
                                       activebackground="#7EEAFF", relief="flat",
                                       cursor="hand2", font=("Segoe UI", 11, "bold"), pady=13)
        self.record_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.save_button = tk.Button(actions, text="●  SON KLİBİ KAYDET", command=self._save,
                                     fg=FG, bg=PANEL2, activeforeground=FG,
                                     activebackground="#32506B", relief="flat",
                                     cursor="hand2", font=("Segoe UI", 11, "bold"), pady=13,
                                     state="disabled")
        self.save_button.pack(side="left", fill="x", expand=True, padx=(8, 0))

        shortcut = tk.Frame(self.root, bg=DARK)
        shortcut.pack(fill="x", padx=30, pady=(14, 0))
        self._label(shortcut, "Ctrl + Shift + F9  =  Başlat / Durdur", 9, MUTED).pack(side="left")
        self._label(shortcut, "Ctrl + Shift + F10  =  Replay kaydet", 9, MUTED).pack(side="right")

        bottom = tk.Frame(self.root, bg=DARK)
        bottom.pack(fill="x", side="bottom", padx=29, pady=(0, 20))
        self._label(bottom, "Klipler: Videolar / ReplayCore", 9, MUTED).pack(side="left")
        tk.Button(bottom, text="Klasörü aç  ↗", command=self._open_folder,
                  bg=DARK, fg=CYAN, activebackground=DARK,
                  activeforeground=CYAN, cursor="hand2", relief="flat",
                  font=("Segoe UI", 10, "bold")).pack(side="right")
        self.notice = self._label(self.root, "", 9, MUTED, wraplength=580)
        self.notice.pack(side="bottom", fill="x", padx=30, pady=(0, 9))

    def _make_combo(self, parent, title, variable, values, column):
        side = tk.Frame(parent, bg=PANEL)
        side.pack(side="left", fill="x", expand=True,
                  padx=(0, 8) if column == 0 else (8, 0))
        self._label(side, title, 10, MUTED).pack(anchor="w", pady=(0, 5))
        combo = ttk.Combobox(side, textvariable=variable, values=values,
                             state="readonly", style="Settings.TCombobox")
        combo.pack(fill="x")
        if not hasattr(self, "setting_combos"):
            self.setting_combos = []
        self.setting_combos.append(combo)

    def _set_status(self, title, subtitle, color=MUTED):
        self.status_head.configure(text=title, fg=color)
        self.status_sub.configure(text=subtitle)

    def _set_editable(self, can_edit):
        for combo in self.setting_combos:
            combo.configure(state="readonly" if can_edit else "disabled")
        self.audio_combo.configure(state="normal" if can_edit else "disabled")
        self.scan_button.configure(state="normal" if can_edit else "disabled")

    def _toggle(self):
        if self.state == "idle":
            selected = self.selected_audio.get().strip()
            settings = Settings(
                duration=int(self.selected_duration.get()),
                fps=int(self.selected_fps.get()),
                resolution=self.selected_resolution.get(),
                encoder=self.selected_encoder.get(),
                audio_device="" if selected == "Ses yok" else selected,
            )
            if self.engine.start(settings):
                self.state = "starting"
                self._set_editable(False)
                self.record_button.configure(text="Başlatılıyor...", state="disabled")
                self.save_button.configure(state="disabled")
                self._set_status("◌  Kayıt motoru hazırlanıyor", "Uygun ekran kartı kodlayıcısı deneniyor...", CYAN)
                self.notice.configure(text="İlk kliplerin oluşması birkaç saniye sürebilir.")
        elif self.state == "recording":
            self.state = "stopping"
            self.record_button.configure(text="Durduruluyor...", state="disabled")
            self.save_button.configure(state="disabled")
            self.engine.stop()

    def _save(self):
        if self.state == "recording":
            self.engine.save(self.output_folder)

    def _scan_audio(self):
        ffmpeg = locate_ffmpeg()
        if not ffmpeg:
            messagebox.showerror("FFmpeg yok", "Önce KUR_FFMPEG.bat dosyasını çalıştır.")
            return
        self.scan_button.configure(state="disabled", text="Aranıyor...")

        def scan():
            devices = audio_devices(ffmpeg)
            self.events.put(("audio_devices", devices))

        threading.Thread(target=scan, daemon=True).start()

    def _open_folder(self):
        self.output_folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(self.output_folder)  # Windows Explorer
        except (OSError, AttributeError):
            self.notice.configure(text=str(self.output_folder))

    def _pump_events(self):
        try:
            while True:
                event, data = self.events.get_nowait()
                if event == "trying":
                    pretty = {"h264_nvenc": "NVIDIA NVENC", "h264_amf": "AMD AMF",
                              "libx264": "CPU x264"}.get(data, str(data))
                    self._set_status("◌  Kodlayıcı deneniyor", pretty, CYAN)
                elif event == "started":
                    self.state = "recording"
                    pretty = {"h264_nvenc": "NVIDIA NVENC", "h264_amf": "AMD AMF",
                              "libx264": "CPU x264"}.get(data, str(data))
                    self._set_status("●  KAYIT AKTİF", f"{pretty} | Son {self.selected_duration.get()} saniye hazır", GREEN)
                    self.record_button.configure(text="■  KAYDI DURDUR", state="normal", bg=RED)
                    self.save_button.configure(state="normal", bg="#2C5268")
                    self.notice.configure(text="Oyun oynarken Ctrl + Shift + F10 ile anında MP4 kaydet.")
                elif event == "stopping":
                    self._set_status("◌  Kayıt durduruluyor", "Açık parçalar kapatılıyor...", MUTED)
                elif event == "stopped":
                    self.state = "idle"
                    self.record_button.configure(text="▶  KAYDI BAŞLAT", state="normal", bg=CYAN)
                    self.save_button.configure(state="disabled", bg=PANEL2)
                    self._set_editable(True)
                    self._set_status("○  Kayıt beklemede", "Yeni kayıt başlatmak için butona bas.", MUTED)
                elif event == "saving":
                    self.notice.configure(text="Klip MP4 olarak kaydediliyor...")
                elif event == "saved":
                    self.notice.configure(text="✓  Kaydedildi: " + str(data))
                elif event == "save_error":
                    self.notice.configure(text="Klip hatası: " + str(data))
                elif event == "error":
                    self.notice.configure(text="Hata: " + str(data))
                    messagebox.showerror("ReplayCore", str(data))
                elif event == "hint":
                    self.notice.configure(text=str(data))
                elif event == "audio_devices":
                    self.scan_button.configure(state="normal", text="Aygıtları tara")
                    options = ["Ses yok"] + list(data)
                    self.audio_combo.configure(values=options)
                    if data:
                        self.notice.configure(text=f"{len(data)} ses aygıtı bulundu. Oyun sesi için Stereo Mix seç.")
                    else:
                        self.notice.configure(text="Ses aygıtı bulunamadı. Sessiz kayıt yapabilirsin.")
                elif event == "shortcut_save":
                    self._save()
                elif event == "shortcut_toggle":
                    self._toggle()
                elif event == "hotkey_info":
                    self.notice.configure(text=str(data))
        except queue.Empty:
            pass
        self.root.after(100, self._pump_events)

    def _close(self):
        self.engine.shutdown()
        self.hotkeys.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
