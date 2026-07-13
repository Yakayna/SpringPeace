# SpringPeace

SpringPeace là GUI/CLI GPL-3.0-or-later để tạo payload candidate từ Android `boot.img` cho CVE-2026-43499. Ứng dụng Windows dùng giao diện SpringPeace, tự kiểm tra ADB, đọc `boot.img`, build các candidate `payload.so`, rồi thử qua ADB theo thứ tự manifest.

SpringPeace is a GPL-3.0-or-later GUI/CLI for generating Android `boot.img` payload candidates for CVE-2026-43499. The Windows app checks ADB, inspects `boot.img`, builds `payload.so` candidates, then tries them through ADB in manifest order.

## Pre-release / Tải bản test

Use the GitHub Release asset `SpringPeace-0.1-pre.zip` for the bundled one-click package. The zip contains:

- `SpringPeace.exe`
- `Tools/platform-tools` (ADB)
- `Tools/android-ndk-r29` (NDK/LLVM)
- `Tools/exploit` (patched exploit engine)
- `Lang/vi.json`, `Lang/en.json`

## Scope note / Lưu ý phạm vi test

**VI:** Bản hiện tại mới test trên Xiaomi và OnePlus/OPPO kernel 6.12.x chạy chip Snapdragon. Thiết bị khác có thể không chạy đúng và có thể reboot.

**EN:** This build has only been tested on Xiaomi and OnePlus/OPPO 6.12.x kernels running Snapdragon chipsets. Other devices may not work and may reboot.

## Temporary-root note / Lưu ý root tạm thời

**VI:** Root kiểu này không ổn định, phù hợp cho các mục đích tạm thời như thay file vào app, thao tác nhanh, unlock bootloader hoặc kiểm thử. Không nên dùng lâu dài; reboot sẽ mất trạng thái.

**EN:** This root style is not stable. Use it for temporary tasks such as replacing app files, quick changes, bootloader-unlock workflows, or testing. It is not for long-term daily use; reboot clears the state.

## How the app works

1. Start ADB and read the connected device list.
2. Inspect `boot.img`: Android header, raw kernel, version string, BTF/kallsyms when available.
3. Build a candidate sweep using common `p0_kernel_phys_load` values because `boot.img` does not always prove the physical-load address.
4. Generate `target.h` and compile `payload.so` with Android NDK/LLVM.
5. Push each runnable candidate through ADB and stop when root is confirmed.

## Upstream credit

SpringPeace wraps and patches the public research implementation from [`x-spy/CVE-2026-43499-popsicle`](https://github.com/x-spy/CVE-2026-43499-popsicle). The app UI intentionally uses the generic term “exploit”; upstream details are documented here.

## Source layout

- `tools/springpeace-oneclick/springpeace_gui.py` — SpringPeace GUI.
- `tools/springpeace-oneclick/springpeace.py` — CLI/core builder.
- `tools/springpeace-oneclick/presets.json` — candidate/preset data.
- `tools/springpeace-oneclick/patches/` — generator compatibility patch.
- `tools/springpeace-oneclick/assets/` — Mika app image/icon from the local user-supplied image.
- `docs/SPRINGPEACE_BOOTIMG_TOOL_NOTES.md` — boot.img/candidate notes.
- `bin/SpringPeace.exe` — convenience GUI build without the large bundled Tools folder.

## Build GUI from source

Install Python 3.14+ and run:

```powershell
python -m pip install --user -r .\tools\springpeace-oneclick\requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\springpeace-oneclick\build_gui_exe.ps1
```

For a fully bundled local package, place these folders beside `SpringPeace.exe`:

```text
Tools\platform-tools\adb.exe
Tools\android-ndk-r29\toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe
Tools\exploit\generate_target.py
```

## License

SpringPeace wrapper code is GPL-3.0-or-later. Upstream exploit code remains under its own repository and license.
