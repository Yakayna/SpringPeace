#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""SpringPeace Material-ish Tkinter GUI."""
from __future__ import annotations

import contextlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import springpeace

APP_NAME = "SpringPeace"
ACCENT = "#6750A4"
ACCENT_2 = "#7D5260"
BG = "#FDF8FF"
CARD = "#FFFFFF"
CARD_2 = "#F7F0FF"
TEXT = "#1D1B20"
MUTED = "#625B71"
OUTLINE = "#E7DFF2"
GREEN = "#146C2E"
RED = "#BA1A1A"

TR = {
    "vi": {
        "lang_name": "VI",
        "headline": "Dựa trên CVE-2026-43499, boot.img → payload để root thiết bị của bạn.",
        "scope": "Bản hiện tại mới test trên Xiaomi và OnePlus/OPPO kernel 6.12.x chạy chip Snapdragon. Thiết bị khác có thể không chạy đúng và có thể reboot.",
        "boot": "boot.img",
        "boot_hint": "Chọn boot.img gốc của firmware thiết bị",
        "output": "Thư mục output (tuỳ chọn)",
        "output_hint": "Để trống: tự tạo thư mục SpringPeace-output",
        "choose": "Chọn",
        "one_click": "One-click Root",
        "build_only": "Build payload thôi",
        "inspect": "Kiểm tra boot.img",
        "open_out": "Mở output",
        "refresh": "Kiểm tra tool",
        "tools": "Công cụ",
        "tools_ready": "ADB / NDK / exploit đã sẵn sàng",
        "adb": "ADB",
        "ndk": "NDK / LLVM",
        "exploit": "Exploit",
        "device": "Thiết bị ADB",
        "connected": "Đã kết nối",
        "not_connected": "Chưa kết nối",
        "root_note_title": "Lưu ý root tạm thời",
        "root_note": "Root kiểu này không ổn định, phù hợp cho các mục đích tạm thời như thay file vào app, thao tác nhanh, unlock bootloader hoặc kiểm thử. Không nên dùng lâu dài; reboot sẽ mất trạng thái.",
        "ready": "Sẵn sàng",
        "missing": "Thiếu",
        "log": "Nhật ký",
        "how_title": "Cách hoạt động",
        "how": (
            "1) Tự khởi động ADB và đọc danh sách thiết bị.\n"
            "2) Kiểm tra boot.img: header, kernel, version, BTF/kallsyms.\n"
            "3) Build nhi\u1ec1u candidate p0load ph\u1ed5 bi\u1ebfn v\u00ec boot.img kh\u00f4ng lu\u00f4n ch\u1ee9a physical-load address ch\u1eafc ch\u1eafn.\n"
            "4) Build target.h + payload.so b\u1eb1ng exploit engine v\u00e0 Android NDK.\n"
            "5) T\u1ef1 push t\u1eebng payload h\u1ee3p l\u1ec7 qua ADB v\u00e0 d\u1eebng khi su tr\u1ea3 uid=0."
        ),
        "sweep_title": "Build candidate sweep là gì?",
        "sweep": (
            "boot.img thường không chứa chắc chắn địa chỉ physical load của kernel. Candidate sweep là build nhiều payload với các p0load phổ biến "
            "\u0111\u1ec3 t\u00ecm b\u1ea3n kh\u1edbp. Trong b\u1ea3n 0.1, One-click d\u00f9ng c\u00e1ch n\u00e0y t\u1ef1 \u0111\u1ed9ng \u0111\u1ec3 kh\u00f4ng c\u1ea7n ch\u1ecdn c\u1ea5u h\u00ecnh."
        ),
        "select_boot_first": "Hãy chọn boot.img trước.",
        "running": "Đang chạy...",
        "done": "Hoàn tất",
        "error": "Lỗi",
        "build_unknown": "\u0110\u00e3 build candidate sweep. One-click s\u1ebd th\u1eed c\u00e1c payload h\u1ee3p l\u1ec7 theo th\u1ee9 t\u1ef1 trong manifest.",
    },
    "en": {
        "lang_name": "EN",
        "headline": "Based on CVE-2026-43499, boot.img → payload to root your device.",
        "scope": "This build has only been tested on Xiaomi and OnePlus/OPPO 6.12.x kernels running Snapdragon chipsets. Other devices may not work and may reboot.",
        "boot": "boot.img",
        "boot_hint": "Select the stock boot.img from the device firmware",
        "output": "Output folder (optional)",
        "output_hint": "Empty: create SpringPeace-output automatically",
        "choose": "Choose",
        "one_click": "One-click Root",
        "build_only": "Build payload only",
        "inspect": "Inspect boot.img",
        "open_out": "Open output",
        "refresh": "Check tools",
        "tools": "Tools",
        "tools_ready": "ADB / NDK / exploit are ready",
        "adb": "ADB",
        "ndk": "NDK / LLVM",
        "exploit": "Exploit",
        "device": "ADB device",
        "connected": "Connected",
        "not_connected": "Not connected",
        "root_note_title": "Temporary root note",
        "root_note": "This root style is not stable. Use it for temporary tasks such as replacing app files, quick changes, bootloader-unlock workflows, or testing. It is not for long-term daily use; reboot clears the state.",
        "ready": "Ready",
        "missing": "Missing",
        "log": "Log",
        "how_title": "How it works",
        "how": (
            "1) Start ADB and read the connected device list.\n"
            "2) Inspect boot.img: header, kernel, version, BTF/kallsyms.\n"
            "3) Build multiple common p0load candidates because boot.img does not always prove the physical-load address.\n"
            "4) Build target.h + payload.so through the exploit engine and Android NDK.\n"
            "5) Push valid payload candidates over ADB and stop when su returns uid=0."
        ),
        "sweep_title": "What is candidate sweep?",
        "sweep": (
            "boot.img often does not prove the kernel physical load address. Candidate sweep builds several payloads with common p0load values "
            "to find a matching build. In 0.1, One-click uses this automatically so no strategy selection is needed."
        ),
        "select_boot_first": "Select boot.img first.",
        "running": "Running...",
        "done": "Done",
        "error": "Error",
        "build_unknown": "Candidate sweep was built. One-click will try valid payloads in manifest order.",
    },
}


class QueueWriter:
    def __init__(self, q: queue.Queue[str]) -> None:
        self.q = q
        self.buf = ""

    def sanitize_log(self, text: str) -> str:
        return (text.replace("x-spy", "exploit")
                    .replace("X-SPY", "exploit")
                    .replace("xspy", "exploit")
                    .replace("profile", "strategy"))

    def write(self, text: str) -> int:
        if not text:
            return 0
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self.q.put(self.sanitize_log(line + "\n"))
        return len(text)

    def flush(self) -> None:
        if self.buf:
            self.q.put(self.sanitize_log(self.buf))
            self.buf = ""


def app_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def tools_dirs() -> list[Path]:
    rd = runtime_dir()
    return [rd / "Tools", rd.parent / "Tools", Path.cwd() / "Tools", Path.cwd() / "tools" / "springpeace-oneclick" / "vendor"]


def first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


class SpringPeaceGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = "vi"
        self.q: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.last_payload: Path | None = None
        self.tool_state: dict[str, object | None] = {"adb": None, "ndk": None, "exploit": None, "device": None}

        self.boot_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.tool_status_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_label_var = tk.StringVar(value="")
        self.progress_max = 1
        self.progress_count = 0

        self.root.title(APP_NAME)
        self.root.geometry("1120x780")
        self.root.minsize(1000, 700)
        self.root.configure(bg=BG)
        self._style()
        self._icon()
        self._build()
        self.set_language("vi")
        self.refresh_tools(log_result=False)
        self.root.after(80, self._drain)

    def t(self, key: str) -> str:
        return TR[self.lang][key]

    def _style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("Glass.TFrame", background=CARD_2, relief="flat")
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.Card.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=CARD_2, foreground=TEXT, font=("Segoe UI", 24, "bold"))
        style.configure("Headline.TLabel", background=CARD_2, foreground=ACCENT_2, font=("Segoe UI", 12, "bold"))
        style.configure("Warn.TLabel", background=CARD_2, foreground=RED, font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), padding=(18, 12), background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", "#7E67BE")], foreground=[("active", "white")])
        style.configure("Soft.TButton", font=("Segoe UI", 10), padding=(12, 8), background="#EADDFF", foreground="#21005D")
        style.map("Soft.TButton", background=[("active", "#D0BCFF")])
        style.configure("TEntry", fieldbackground="white", padding=8)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))

    def _icon(self) -> None:
        ico = app_dir() / "assets" / "mika.ico"
        if ico.exists():
            try:
                self.root.iconbitmap(str(ico))
            except Exception:
                pass

    def _logo(self) -> tk.PhotoImage | None:
        png = app_dir() / "assets" / "mika.png"
        if not png.exists():
            return None
        try:
            im = tk.PhotoImage(file=str(png))
            return im.subsample(3, 3) if im.width() > 240 else im
        except Exception:
            return None

    def card(self, parent, bg=CARD, padx=16, pady=14):
        outer = tk.Frame(parent, bg=OUTLINE, bd=0)
        inner = tk.Frame(outer, bg=bg, bd=0, padx=padx, pady=pady)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        return outer, inner

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG, padx=18, pady=18)
        shell.pack(fill=tk.BOTH, expand=True)

        # Header / liquid-glass-ish hero.
        h_outer, h = self.card(shell, bg=CARD_2, padx=18, pady=18)
        h_outer.pack(fill=tk.X)
        self.logo_img = self._logo()
        if self.logo_img:
            tk.Label(h, image=self.logo_img, bg=CARD_2).pack(side=tk.LEFT, padx=(0, 18))
        title_area = tk.Frame(h, bg=CARD_2)
        title_area.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.title_lbl = ttk.Label(title_area, text=APP_NAME, style="Title.TLabel")
        self.title_lbl.pack(anchor=tk.W)
        self.headline_lbl = ttk.Label(title_area, text="", style="Headline.TLabel", wraplength=820)
        self.headline_lbl.pack(anchor=tk.W, pady=(4, 6))
        self.scope_lbl = ttk.Label(title_area, text="", style="Warn.TLabel", wraplength=840)
        self.scope_lbl.pack(anchor=tk.W)
        self.root_note_lbl = ttk.Label(title_area, text="", style="Warn.TLabel", wraplength=840)
        self.root_note_lbl.pack(anchor=tk.W, pady=(4, 0))
        lang_box = tk.Frame(h, bg=CARD_2)
        lang_box.pack(side=tk.RIGHT, padx=(12, 0))
        self.vi_btn = ttk.Button(lang_box, text="VI", command=lambda: self.set_language("vi"), style="Soft.TButton")
        self.vi_btn.pack(fill=tk.X, pady=2)
        self.en_btn = ttk.Button(lang_box, text="EN", command=lambda: self.set_language("en"), style="Soft.TButton")
        self.en_btn.pack(fill=tk.X, pady=2)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        left = tk.Frame(body, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right = tk.Frame(body, bg=BG, width=330)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        input_outer, input_card = self.card(left, bg=CARD)
        input_outer.pack(fill=tk.X)
        self.boot_lbl = tk.Label(input_card, bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold"))
        self.boot_lbl.grid(row=0, column=0, sticky="w", pady=(0, 4))
        input_card.columnconfigure(0, weight=1)
        row = tk.Frame(input_card, bg=CARD)
        row.grid(row=1, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)
        self.boot_entry = ttk.Entry(row, textvariable=self.boot_var)
        self.boot_entry.grid(row=0, column=0, sticky="ew")
        self.boot_btn = ttk.Button(row, text="", command=self.choose_boot, style="Soft.TButton")
        self.boot_btn.grid(row=0, column=1, padx=(8, 0))
        self.boot_hint_lbl = tk.Label(input_card, bg=CARD, fg=MUTED, font=("Segoe UI", 9))
        self.boot_hint_lbl.grid(row=2, column=0, sticky="w", pady=(4, 12))

        self.output_lbl = tk.Label(input_card, bg=CARD, fg=TEXT, font=("Segoe UI", 10, "bold"))
        self.output_lbl.grid(row=3, column=0, sticky="w", pady=(0, 4))
        outrow = tk.Frame(input_card, bg=CARD)
        outrow.grid(row=4, column=0, sticky="ew")
        outrow.columnconfigure(0, weight=1)
        self.output_entry = ttk.Entry(outrow, textvariable=self.output_var)
        self.output_entry.grid(row=0, column=0, sticky="ew")
        self.output_btn = ttk.Button(outrow, text="", command=self.choose_output, style="Soft.TButton")
        self.output_btn.grid(row=0, column=1, padx=(8, 0))
        self.output_hint_lbl = tk.Label(input_card, bg=CARD, fg=MUTED, font=("Segoe UI", 9))
        self.output_hint_lbl.grid(row=5, column=0, sticky="w", pady=(4, 0))

        actions = tk.Frame(left, bg=BG)
        actions.pack(fill=tk.X, pady=12)
        self.one_btn = ttk.Button(actions, text="", command=self.one_click, style="Accent.TButton")
        self.one_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.build_btn = ttk.Button(actions, text="", command=self.build_only, style="Soft.TButton")
        self.build_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.inspect_btn = ttk.Button(actions, text="", command=self.inspect_only, style="Soft.TButton")
        self.inspect_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.open_btn = ttk.Button(actions, text="", command=self.open_output, style="Soft.TButton")
        self.open_btn.pack(side=tk.LEFT)

        progress_row = tk.Frame(left, bg=BG)
        progress_row.pack(fill=tk.X, pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_row, variable=self.progress_var, maximum=1, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_label = tk.Label(progress_row, textvariable=self.progress_label_var, bg=BG, fg=MUTED, font=("Segoe UI", 9), width=22, anchor="e")
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))

        log_outer, log_card = self.card(left, bg="#10131C", padx=10, pady=10)
        log_outer.pack(fill=tk.BOTH, expand=True)
        self.log_title = tk.Label(log_card, bg="#10131C", fg="#EADDFF", font=("Segoe UI", 11, "bold"))
        self.log_title.pack(anchor=tk.W, pady=(0, 6))
        log_row = tk.Frame(log_card, bg="#10131C")
        log_row.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_row, bg="#10131C", fg="#F8F3FF", insertbackground="#F8F3FF", bd=0, wrap=tk.WORD, font=("Consolas", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_row, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

        tools_outer, tools_card = self.card(right, bg=CARD)
        tools_outer.pack(fill=tk.X)
        self.tools_title = tk.Label(tools_card, bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.tools_title.pack(anchor=tk.W)
        self.tools_status = tk.Label(tools_card, textvariable=self.tool_status_var, bg=CARD, fg=MUTED, justify=tk.LEFT, wraplength=285)
        self.tools_status.pack(anchor=tk.W, fill=tk.X, pady=(8, 8))
        self.refresh_btn = ttk.Button(tools_card, text="", command=lambda: self.refresh_tools(log_result=True), style="Soft.TButton")
        self.refresh_btn.pack(anchor=tk.W)

        how_outer, how_card = self.card(right, bg=CARD)
        how_outer.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.how_title = tk.Label(how_card, bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.how_title.pack(anchor=tk.W)
        self.how_body = tk.Label(how_card, bg=CARD, fg=MUTED, justify=tk.LEFT, wraplength=285, font=("Segoe UI", 9))
        self.how_body.pack(anchor=tk.W, pady=(8, 12), fill=tk.X)
        self.sweep_title = tk.Label(how_card, bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold"))
        self.sweep_title.pack(anchor=tk.W)
        self.sweep_body = tk.Label(how_card, bg=CARD, fg=MUTED, justify=tk.LEFT, wraplength=285, font=("Segoe UI", 9))
        self.sweep_body.pack(anchor=tk.W, pady=(8, 0), fill=tk.X)

        self.status_lbl = tk.Label(shell, textvariable=self.status_var, bg=BG, fg=MUTED, anchor="w", font=("Segoe UI", 9))
        self.status_lbl.pack(fill=tk.X, pady=(8, 0))

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self.root.title(APP_NAME)
        self.headline_lbl.configure(text=self.t("headline"))
        self.scope_lbl.configure(text=self.t("scope"))
        self.root_note_lbl.configure(text=f"{self.t("root_note_title")}: {self.t("root_note")}")
        self.boot_lbl.configure(text=self.t("boot"))
        self.boot_hint_lbl.configure(text=self.t("boot_hint"))
        self.output_lbl.configure(text=self.t("output"))
        self.output_hint_lbl.configure(text=self.t("output_hint"))
        self.boot_btn.configure(text=self.t("choose"))
        self.output_btn.configure(text=self.t("choose"))
        self.one_btn.configure(text=self.t("one_click"))
        self.build_btn.configure(text=self.t("build_only"))
        self.inspect_btn.configure(text=self.t("inspect"))
        self.open_btn.configure(text=self.t("open_out"))
        self.refresh_btn.configure(text=self.t("refresh"))
        self.tools_title.configure(text=self.t("tools"))
        self.log_title.configure(text=self.t("log"))
        self.how_title.configure(text=self.t("how_title"))
        self.how_body.configure(text=self.t("how"))
        self.sweep_title.configure(text=self.t("sweep_title"))
        self.sweep_body.configure(text=self.t("sweep"))
        self.status_var.set(self.t("ready"))
        self._render_tool_status()

    def log(self, text: str) -> None:
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def reset_progress(self, maximum: int = 1, label: str = "") -> None:
        self.progress_max = max(1, int(maximum))
        self.progress_count = 0
        self.progress_bar.configure(maximum=self.progress_max, mode="determinate")
        self.progress_var.set(0)
        self.progress_label_var.set(label)

    def bump_progress(self) -> None:
        self.progress_count = min(self.progress_max, self.progress_count + 1)
        self.progress_var.set(self.progress_count)
        self.progress_label_var.set(f"{self.progress_count}/{self.progress_max}")

    def _drain(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                if "built payload_p0load_" in msg or "target generation failed for p0load" in msg or "build failed for p0load" in msg:
                    self.bump_progress()
                self.log(msg)
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def choose_boot(self) -> None:
        path = filedialog.askopenfilename(title="boot.img", filetypes=[("Android boot image", "*.img"), ("All files", "*.*")])
        if path:
            self.boot_var.set(path)

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="Output")
        if path:
            self.output_var.set(path)

    def default_output(self) -> Path:
        if self.output_var.get().strip():
            return Path(self.output_var.get()).resolve()
        boot = self.boot_var.get().strip()
        if boot:
            return (Path(boot).resolve().parent / "SpringPeace-output").resolve()
        return (Path.home() / "SpringPeace-output").resolve()

    def find_adb(self) -> Path | None:
        exe = "adb.exe" if os.name == "nt" else "adb"
        candidates: list[Path] = []
        for td in tools_dirs():
            candidates += [td / "platform-tools" / exe, td / exe]
        path_hit = shutil.which("adb")
        if path_hit:
            candidates.append(Path(path_hit))
        return first_existing(candidates)

    def find_ndk(self) -> Path | None:
        candidates: list[Path] = []
        for td in tools_dirs():
            candidates += [td / "android-ndk-r29", td / "android-ndk-r29-windows" / "android-ndk-r29", td / "ndk" / "android-ndk-r29"]
        for env in ("ANDROID_NDK_HOME", "ANDROID_NDK_ROOT", "NDK_ROOT"):
            if os.environ.get(env):
                candidates.append(Path(os.environ[env]))
        for c in candidates:
            if (c / "toolchains" / "llvm" / "prebuilt").exists():
                return c
        return None

    def find_bundled_exploit(self) -> Path | None:
        candidates: list[Path] = []
        for td in tools_dirs():
            candidates += [td / "exploit", td / "exploit"]
        candidates += [app_dir() / "vendor" / "exploit", app_dir() / "vendor" / "exploit"]
        for c in candidates:
            if (c / "generate_target.py").exists() and (c / "source" / "src").exists():
                return c
        return None


    def refresh_tools(self, log_result: bool = True) -> None:
        self.tool_state["adb"] = self.find_adb()
        self.tool_state["ndk"] = self.find_ndk()
        self.tool_state["exploit"] = self.find_bundled_exploit()
        self.tool_state["device"] = None
        if self.tool_state.get("adb"):
            try:
                subprocess.run([str(self.tool_state["adb"]), "start-server"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **springpeace.hidden_subprocess_kwargs())
                p = subprocess.run([str(self.tool_state["adb"]), "devices"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **springpeace.hidden_subprocess_kwargs())
                for line in p.stdout.splitlines():
                    if "\tdevice" in line:
                        self.tool_state["device"] = line.split()[0]
                        break
                if log_result:
                    self.q.put("[adb-devices]\n" + p.stdout + "\n")
            except Exception as exc:
                if log_result:
                    self.q.put(f"[adb] connection check error: {exc}\n")
        self._render_tool_status()
        if log_result:
            self.q.put("\n[tools]\n")
            for k, v in self.tool_state.items():
                self.q.put(f"  {k}: {v if v else 'missing'}\n")


    def _render_tool_status(self) -> None:
        def mark_path(key: str, label: str) -> str:
            return f"? {label}: {self.t('ready')}" if self.tool_state.get(key) else f"? {label}: {self.t('missing')}"
        device_value = self.tool_state.get("device")
        device_line = f"? {self.t('device')}: {self.t('connected')} ({device_value})" if device_value else f"? {self.t('device')}: {self.t('not_connected')}"
        text = "\n".join([
            mark_path("adb", self.t("adb")),
            device_line,
            mark_path("ndk", self.t("ndk")),
            mark_path("exploit", self.t("exploit")),
        ])
        self.tool_status_var.set(text)
        color = GREEN if all(self.tool_state.values()) else RED
        self.tools_status.configure(fg=color)


    def ensure_exploit_work(self, out_dir: Path) -> Path:
        src = self.tool_state.get("exploit") or self.find_bundled_exploit()
        if not src:
            raise RuntimeError("Bundled exploit source missing")
        work = out_dir / "_springpeace_exploit"
        if work.exists():
            shutil.rmtree(work)
        ignore = shutil.ignore_patterns(".git", "build", "__pycache__", "*.pyc")
        shutil.copytree(src, work, ignore=ignore)
        return work

    def adb_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        adb = self.tool_state.get("adb") or self.find_adb()
        if not adb:
            raise RuntimeError("ADB missing")
        return subprocess.run([str(adb), *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **springpeace.hidden_subprocess_kwargs())

    def start_adb_and_check(self) -> None:
        self.q.put("[adb] start-server\n")
        p = self.adb_cmd("start-server")
        self.q.put(p.stdout)
        p = self.adb_cmd("devices")
        self.q.put(p.stdout)
        lines = [ln for ln in p.stdout.splitlines() if "\tdevice" in ln]
        if not lines:
            self.q.put("[adb] no online device detected yet. Build can continue; run step may fail.\n")

    def inspect_info(self) -> springpeace.BootInfo:
        boot = Path(self.boot_var.get().strip())
        if not boot.exists():
            raise RuntimeError(self.t("select_boot_first"))
        info = springpeace.inspect_boot(boot)
        self.q.put(json.dumps(info.__dict__ | {"path": str(info.path)}, indent=2, default=str) + "\n")
        return info

    def choose_strategy(self, info: springpeace.BootInfo) -> tuple[str, bool]:
        # 0.1 uses the generic candidate strategy only; no visible kernel selection.
        return "common-arm64-candidates", True

    def sanitize_log(self, text: str) -> str:
        return (text.replace("exploit", "exploit")
                    .replace("X-SPY", "exploit")
                    .replace("exploit", "exploit")
                    .replace("strategy", "strategy"))


    def run_springpeace(self, args: list[str]) -> int:
        writer = QueueWriter(self.q)
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            rc = springpeace.main(args)
        writer.flush()
        return rc

    def build_payload(self, auto_run: bool) -> tuple[list[Path], bool]:
        self.refresh_tools(log_result=False)
        if not self.tool_state.get("ndk"):
            raise RuntimeError("NDK / LLVM missing. Put android-ndk-r29 in Tools/android-ndk-r29 or set ANDROID_NDK_HOME.")
        out = self.default_output()
        out.mkdir(parents=True, exist_ok=True)
        exploit_work = self.ensure_exploit_work(out)
        info = self.inspect_info()
        strategy, runnable = self.choose_strategy(info)
        candidate_count = len(springpeace.load_presets().get("common-arm64-candidates", {}).get("candidate_loads", [])) or 1
        self.root.after(0, lambda c=candidate_count: self.reset_progress(c, f"0/{c}"))
        self.q.put(f"[strategy] generic candidates; auto_run={auto_run}; candidates={candidate_count}\n")
        self.q.put("[progress] Building candidates. This is normal; it stops after the listed candidate count.\n")
        args = [
            "make",
            "--boot", self.boot_var.get().strip(),
            "--preset", strategy,
            "--xspy-repo", str(exploit_work),
            "--ndk", str(self.tool_state["ndk"]),
            "--out", str(out),
            "--python", "INPROCESS",
        ]
        rc = self.run_springpeace(args)
        if rc != 0:
            raise RuntimeError(f"build failed rc={rc}")
        manifest = out / "manifest.json"
        payloads: list[Path] = []
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
            built = [c for c in data.get("candidates", []) if c.get("payload") and c.get("layout_ok") is not False]
            # Use manifest order. common-arm64-candidates is ordered for 0.1: a800 first, c780 second, then generic fallbacks.
            for c in built:
                payloads.append(Path(c["payload"]))
        if not payloads:
            raise RuntimeError("no runnable payload built")
        self.last_payload = payloads[0]
        shutil.copy2(payloads[0], out / "payload.so")
        self.q.put(f"[payload-primary] {payloads[0]}\n")
        self.q.put(f"[payload-copy] {out / 'payload.so'}\n")
        self.q.put(f"[payload-count] {len(payloads)} candidate(s) ready\n")
        return payloads, bool(auto_run and runnable)


    def run_payload_candidates_adb(self, payloads: list[Path]) -> None:
        self.root.after(0, lambda n=len(payloads): self.reset_progress(n, f"root 0/{n}"))
        for idx, payload in enumerate(payloads, 1):
            self.q.put(f"[adb] try candidate {idx}/{len(payloads)}: {payload}\n")
            commands = [
                ("push", str(payload), "/data/local/tmp/preload.so"),
                ("shell", "chmod", "0644", "/data/local/tmp/preload.so"),
                ("shell", "LD_PRELOAD=/data/local/tmp/preload.so /system/bin/true"),
                ("shell", "/data/local/tmp/su", "-c", "id"),
            ]
            success = False
            for args in commands:
                p = self.adb_cmd(*args)
                self.q.put(p.stdout)
                if p.returncode != 0:
                    self.q.put(f"[adb] command rc={p.returncode}: {' '.join(args)}\n")
                    break
                if args[:2] == ("shell", "/data/local/tmp/su") and "uid=0" in p.stdout:
                    success = True
            self.root.after(0, self.bump_progress)
            if success:
                self.root.after(0, lambda n=len(payloads): self.progress_label_var.set(f"root OK {idx}/{n}"))
                self.q.put("[adb] root OK: uid=0\n")
                return
            p = self.adb_cmd("get-state")
            if p.returncode != 0 or "device" not in p.stdout:
                self.q.put("[adb] device not online after this candidate; stop.\n")
                return
        self.q.put("[adb] tried all candidates; root shell was not confirmed.\n")


    def run_task(self, title: str, fn) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo(APP_NAME, self.t("running"))
            return
        self.status_var.set(self.t("running"))
        self.reset_progress(1, "")
        self.q.put(f"\n=== {title} @ {time.strftime('%H:%M:%S')} ===\n")

        def runit() -> None:
            try:
                fn()
                self.q.put(f"=== {self.t('done')} ===\n")
                self.root.after(0, lambda: self.status_var.set(self.t("done")))
            except BaseException as exc:
                self.q.put(f"[!] {type(exc).__name__}: {exc}\n")
                self.root.after(0, lambda: self.status_var.set(self.t("error")))

        self.worker_thread = threading.Thread(target=runit, daemon=True)
        self.worker_thread.start()

    def one_click(self) -> None:
        def task() -> None:
            self.refresh_tools(log_result=True)
            self.start_adb_and_check()
            payloads, should_run = self.build_payload(auto_run=True)
            if should_run and payloads:
                self.run_payload_candidates_adb(payloads)
        self.run_task(self.t("one_click"), task)

    def build_only(self) -> None:
        self.run_task(self.t("build_only"), lambda: self.build_payload(auto_run=False))

    def inspect_only(self) -> None:
        self.run_task(self.t("inspect"), lambda: self.inspect_info())

    def open_output(self) -> None:
        out = self.default_output()
        out.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(out))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(out)])


def main() -> int:
    if "--selftest" in sys.argv:
        assert springpeace.load_presets()
        assert (app_dir() / "assets" / "mika.png").exists() or not getattr(sys, "frozen", False)
        print("SpringPeace GUI selftest OK")
        return 0
    springpeace.configure_console_encoding()
    root = tk.Tk()
    SpringPeaceGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
