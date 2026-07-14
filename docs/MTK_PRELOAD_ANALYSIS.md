# MTK preload.so analysis — Redmi K80 Ultra sample

Time: 2026-07-14 +07:00

Sample:

```text
C:\Users\Yakayn\Downloads\AyuGram Desktop\preload.so
size: 4,712,936 bytes
sha256: 8207a2a9becb9e68c03a800829b30f7745bd0d326d683e92a7503a42b75cdb30
```

## ELF summary

- ELF64 little-endian `DYN` shared object for `AArch64`.
- Main code section `.text`: `0xae70` bytes.
- Huge `.rodata`: `0x464d31` bytes, because the payload embeds helper artifacts.
- Symbol table is present, so `llvm-readelf`, `llvm-nm`, and `llvm-objdump` were enough; IDA is optional for deeper function graph review.

## Embedded payloads inside rodata

Extracted from symbols:

```text
embedded_su_start       0x00009780
embedded_su_end         0x0000ce48   size 14,024 bytes   ELF64 AArch64
embedded_wallpaper_start 0x0000ce50
embedded_wallpaper_end   0x0001299c  size 23,372 bytes   WEBP/RIFF
embedded_ksud_start     0x000129a0
embedded_ksud_end       0x0046afe0   size 4,556,352 bytes ELF64 AArch64
```

This explains why the file is much larger than the normal Snapdragon payload candidates. It is not only a small `LD_PRELOAD` trigger; it carries `su`, `ksud`/KernelSU userspace, and a small WEBP asset.

## Exploit route/features seen in symbols and strings

Important symbols present:

```text
p0_data_alias
p0_alias_image_offset
slide_leak_kernel_base
prepare_slide_pselect_fdsets
do_pselect_fake_lock_route
install_pipe_physrw
pipe_phys_read / pipe_phys_write
find_pipe_buffer / forge_pipe_buffers_on_page
install_android_root
install_embedded_su / install_embedded_ksud
patch_cred_identity / patch_cred_object / patch_cred_sid
```

Runtime log strings show these stages:

```text
preload starting pid=%d
build config pid=%d label=%s slide=pselect main=pselect
p0 profile pid=%d phys_offset=%016llx kernel_phys_load=%016llx delta=%016llx ...
slide-kaslr-ok pid=%d base=%016llx slide=%016llx
pipe-physrw-summary pid=%d done=%d root=%d kaslr=%d ...
root child result ... embedded_su=... selinux=... cap=...
```

So this MTK payload appears to use the same pselect/KASLR idea, then switches into a pipe physical read/write route and finally installs temporary Android root plus embedded `su`/KernelSU userspace.

## MTK p0 mapping extracted from code

Function `p0_data_alias` disassembles to:

```asm
mov x8, #0x3f80000000
add x8, x0, x8
orr x0, x8, #0xffffff8000000000
ret
```

Meaning:

```text
P0_PAGE_OFFSET          = 0xffffff8000000000
P0_KERNEL_PHYS_DELTA   = 0x3f80000000
P0_PHYS_OFFSET         = 0x80000000        (same assumption as current generator)
P0_KERNEL_PHYS_LOAD    = 0x4000000000      (delta + phys_offset)
```

This is the most useful value for SpringPeace MTK mode. The current Snapdragon sweep uses low candidates like `0xa8000000` and `0xc7800000`; the Redmi K80 Ultra MTK sample points to high physical load `0x4000000000`.

## Other hardcoded image/data addresses seen

Representative constants recovered from calls to `data_addr`, `text_addr`, and `p0_data_alias`:

```text
0xffffffc0812c9df0  used by leak_kernel_base via p0_data_alias
0xffffffc082315f68  used by install_android_root via data_addr
0xffffffc08164fb68  used by install_android_root via data_addr
0xffffffc0820de7d0  used by install_android_root / task walk helpers
0xffffffc08114a288  pipe_buf_ops text anchor
0xffffffc0803c0394  fops/CFI text anchor
0xffffffc080c7ad08  fops text repair anchor
0xffffffc080c7ad5c  fops text repair anchor
0xffffffc080c7b004  fops text repair anchor
0xffffffc080c7b090  fops text repair anchor
```

These are kernel-build-specific. They should not be copied blindly into another device. SpringPeace should regenerate them from that device's `boot.img`.

## Can we use this payload directly?

- For the exact Redmi K80 Ultra firmware/kernel that produced it: likely yes, as a standalone `preload.so` candidate.
- For another MTK phone or another firmware version: not as-is. It contains hardcoded image/data addresses, task/cred offsets, KASLR anchors, pipe/fops anchors, and an MTK-specific p0 load. A mismatch can simply fail or reboot the device.
- For SpringPeace: use it as a reference to seed MTK mode, especially `P0_KERNEL_PHYS_LOAD=0x4000000000` and the need for a looser kallsyms marker detector. Do not treat the binary as a universal MTK payload.

## SpringPeace changes made from this analysis

- Added `common-mtk-candidates` preset:

```text
0x4000000000
0x4080000000
0x4100000000
0x4800000000
0x80000000
0xc7800000
```

- Added GUI choice:
  - `Snapdragon (hiện tại)` / `Snapdragon (current)`
  - `MTK thử nghiệm` / `MTK experimental`
- Added a loose kallsyms marker-scan hotfix to the generator patch. This targets failures like:

```text
kallsyms markers 候选不唯一: []
```

The MTK mode remains experimental and still requires a correct stock `boot.img` for the exact firmware.
