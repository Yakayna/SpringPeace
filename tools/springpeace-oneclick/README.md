# SpringPeace One-Click

This folder contains the SpringPeace GUI and CLI builder.

- GUI entry: `springpeace_gui.py`
- CLI/core entry: `springpeace.py`
- Build GUI: `build_gui_exe.ps1`
- Build CLI helper: `build_exe.ps1`

## Notes

VI: Bản hiện tại mới test trên Xiaomi và OnePlus/OPPO kernel 6.12.x chạy chip Snapdragon. Thiết bị khác có thể không chạy đúng và có thể reboot.

EN: This build has only been tested on Xiaomi and OnePlus/OPPO 6.12.x kernels running Snapdragon chipsets. Other devices may not work and may reboot.

VI: Root kiểu này không ổn định, phù hợp cho các mục đích tạm thời như thay file vào app, thao tác nhanh, unlock bootloader hoặc kiểm thử. Không nên dùng lâu dài; reboot sẽ mất trạng thái.

EN: This root style is not stable. Use it for temporary tasks such as replacing app files, quick changes, bootloader-unlock workflows, or testing. It is not for long-term daily use; reboot clears the state.

## Build

```powershell
python -m pip install --user -r .\tools\springpeace-oneclick\requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\springpeace-oneclick\build_gui_exe.ps1
```

## Tool folders for packaged builds

The pre-release zip bundles these folders beside `SpringPeace.exe`:

```text
Tools\platform-tools
Tools\android-ndk-r29
Tools\exploit
```

If building from source, provide the same folders or set `ANDROID_NDK_HOME` for CLI usage. The GUI prefers package-local `Tools` folders.

## Upstream

SpringPeace wraps the public research implementation from `x-spy/CVE-2026-43499-popsicle` and applies the compatibility patch in `patches/`.

## License

SpringPeace wrapper code is GPL-3.0-or-later.
