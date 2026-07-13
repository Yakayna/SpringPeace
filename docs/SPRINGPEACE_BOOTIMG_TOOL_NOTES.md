# SpringPeace boot.img → offset/payload notes

Thời điểm cập nhật: 2026-07-13 +07:00.

## Lưu ý phạm vi test / Scope note

- VI: Bản hiện tại mới test trên Xiaomi và OnePlus/OPPO kernel 6.12.x chạy chip Snapdragon. Thiết bị khác có thể không chạy đúng và có thể reboot.
- EN: This build has only been tested on Xiaomi and OnePlus/OPPO 6.12.x kernels running Snapdragon chipsets. Other devices may not work and may reboot.

## Lưu ý root tạm thời / Temporary-root note

- VI: Root kiểu này không ổn định, phù hợp cho các mục đích tạm thời như thay file vào app, thao tác nhanh, unlock bootloader hoặc kiểm thử. Không nên dùng lâu dài; reboot sẽ mất trạng thái.
- EN: This root style is not stable. Use it for temporary tasks such as replacing app files, quick changes, bootloader-unlock workflows, or testing. It is not for long-term daily use; reboot clears the state.

## GUI SpringPeace 0.1-pre

- Tên app: `SpringPeace`.
- UI có VI/EN, logo từ `assets/mika.png`, không hiển thị preset kernel đã biết.
- Panel `Công cụ` kiểm tra ADB, thiết bị ADB, NDK/LLVM và exploit engine.
- `One-click Root` tự chạy: kiểm tra tool → khởi động ADB → kiểm tra thiết bị → kiểm tra boot.img → build candidate sweep → thử từng payload qua ADB.
- Progress bar dùng cho cả giai đoạn build candidate và giai đoạn thử root.
- Cửa sổ cmd khi gọi ADB/LLVM/PyInstaller được ẩn ở chế độ GUI.

## Build candidate sweep là gì?

`boot.img` thường không chứng minh chắc chắn địa chỉ physical-load của kernel. Candidate sweep build nhiều payload với các `p0_kernel_phys_load` phổ biến, lưu từng `target_p0load_<hex>.h`, `payload_p0load_<hex>.so` và `manifest.json`, rồi One-click thử các payload hợp lệ theo thứ tự manifest.

Trong 0.1-pre, thứ tự candidate common ưu tiên OnePlus đã xác nhận trước:

```text
0xa8000000, 0xc7800000, 0x80000000, 0x88000000, 0x90000000,
0x98000000, 0xa0000000, 0xb0000000, 0xb8000000, 0xc0000000
```

## Kết quả OnePlus 15R boot-only

Nguồn boot gốc:

- `D:\OxygenOS_v1.2_CPH2769_OS16.0.8.300_4aa01_Official\firmware-update\boot.img`
- SHA-256 boot.img: `6326c46d790690d534bdd3ce0714b88f9de691fc712e53f61e114fc75d484c64`
- Android boot header: v4, header size `0x630`, kernel offset `0x1000`, kernel size `0x262ba00`
- Kernel SHA-256: `e2efc9dcae2d180e22c85b5d760776b232178dfa758784cf94df3bc2df39147f`
- Kernel: raw arm64 Image, `text_offset=0`, `image_size=0x26e0000`, flags `0xa`
- Version string: `6.12.38-android16-5-g844001fb8721-ab14552068-4k`
- Candidate khớp sau khi build boot-only và đối chiếu: `p0_kernel_phys_load=0xa8000000`.

Payload OnePlus đã tạo:

- SHA-256: `38a727b93c39c9455a9f84767401550288702929cef77701a7ad9cd6a870cd5d`
- Size: `85464` bytes

Macro quan trọng:

```c
#define KIMAGE_TEXT_BASE 0xffffffc080000000ULL
#define P0_PAGE_OFFSET 0xffffff8000000000ULL
#define P0_PHYS_OFFSET 0x80000000ULL
#define P0_KERNEL_PHYS_LOAD 0xa8000000ULL
#define PSELECT_WAITER_WORD_SHIFT 2
#define INIT_TASK 0xffffffc08240cf00ULL
#define INIT_CRED 0xffffffc082422c70ULL
#define ENTRY_TASK 0xffffffc0823b2400ULL
#define PER_CPU_OFFSET 0xffffffc0823fb810ULL
#define ROOT_TASK_GROUP 0xffffffc08263d580ULL
#define SELINUX_ENFORCING 0xffffffc0826894d0ULL
#define TASK_REAL_CRED_OFF 0x8f8
#define TASK_CRED_OFF 0x900
```

## Máy nào nên dùng gì

### OnePlus/OPPO kernel 6.12.x Snapdragon

- Boot kind thường là raw arm64 Image.
- Candidate OnePlus 15R đã khớp: `0xa8000000`.
- `PSELECT_WAITER_WORD_SHIFT=2`, route pselect hợp lệ.
- Dùng common candidate sweep trong app; không cần chọn preset thủ công.

### Xiaomi/Redmi popsicle family Snapdragon kernel 6.12.x

- Dùng common candidate sweep.
- Candidate upstream thường thấy: `0xc7800000`.
- Một số máy cần candidate khác tùy physical load thực tế.

### Redmi Turbo 5 Max sample hiện tại

- Boot kind: LZ4 legacy.
- Static offsets/BTF sinh được từ `boot.img`.
- Vướng chính trong lần thử là route pselect: `PSELECT_WAITER_WORD_SHIFT=6`, các waiter word vượt vùng `nfds=320`.
- Log đã thấy: `slide pselect layout invalid; skip syscall to avoid bad waiter`.
- Hướng tiếp theo: giữ boot offset mới, nhưng cần route/object rewrite kiểu PR #22/#36 hoặc syscall khác có stack object phù hợp; chỉ thay `target.h` chưa đủ.

## Source cần cho open source

```text
tools/springpeace-oneclick/springpeace_gui.py
tools/springpeace-oneclick/springpeace.py
tools/springpeace-oneclick/presets.json
tools/springpeace-oneclick/requirements.txt
tools/springpeace-oneclick/build_gui_exe.ps1
tools/springpeace-oneclick/build_exe.ps1
tools/springpeace-oneclick/assets/mika.png
tools/springpeace-oneclick/assets/mika.ico
tools/springpeace-oneclick/patches/xspy-generate-target-compat.patch
docs/SPRINGPEACE_BOOTIMG_TOOL_NOTES.md
```

Không đưa ROM, `boot.img`, payload cá nhân, log lớn, build cache hoặc full NDK vào git. Full package có `Tools` được đưa lên GitHub Release.

## Hotfix 0.1-pre build 2

- Sửa lỗi `RuntimeError: lost sys.stdin` khi GUI windowed gặp lỗi trong backend.
- `Tools\exploit` đã patch sẵn thì không gọi `git apply`, tránh lỗi `[WinError 2] The system cannot find the file specified` trên máy không có `git` trong PATH.
- Nếu còn thiếu executable khác, log mới sẽ ghi rõ `missing executable: ...` để biết thiếu ADB/clang/objdump/git hay file khác.
