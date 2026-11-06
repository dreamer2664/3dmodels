#!/usr/bin/env python3
"""denoise_images.py — clean up Cycles renders on machines without enough RAM for OIDN.

OpenImageDenoise (Blender's default denoiser) can allocate well over a gigabyte at 1600px
and gets OOM-killed in small sandboxes, which kills the whole render. This script removes
most of the residual sampling noise *after* the fact, using a fast edge-preserving /
bilateral-style filter that needs only a few hundred MB.

It is NOT a replacement for a properly sampled render: render with the rig first
(tools/render_rig.py handles the denoise decision automatically). This is the cleanup
step for the low-RAM path.

Usage (plain Python 3, needs numpy + Pillow):

    python3 tools/denoise_images.py renders/
    python3 tools/denoise_images.py renders/*.png --strength 0.6
    python3 tools/denoise_images.py renders/ --strength 0.9 --sharpen 0.25

Options:
    --strength F   blend amount, 0 = untouched, 1 = fully filtered (default 0.75)
    --radius N     filter radius in pixels (default 2)
    --sharpen F    unsharp mask amount to restore edge crispness (default 0.2)
    --sigma-color  range sigma for the bilateral weight (default 0.10)
    --dry-run      report what would change, write nothing

Exit codes: 0 = ok (or nothing to do), 2 = numpy/Pillow missing, 1 = an image failed.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

def load_deps():
    try:
        import numpy as np
        from PIL import Image
        return np, Image
    except Exception as exc:  # noqa: BLE001
        print(f"error: numpy + Pillow are required ({exc}).\n"
              f"  pip install numpy pillow  (or: pip install --break-system-packages numpy pillow)\n"
              f"  Blender's bundled numpy is not available to the system python; run the render\n"
              f"  rig's own denoise path instead, or install these two packages.", file=sys.stderr)
        return None, None


def box_blur(arr, radius):
    """Separable box blur via cumulative sums (fast, low memory)."""
    np = load_deps()[0]
    out = arr.astype(np.float32, copy=True)
    for axis in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[axis] = (radius + 1, radius)
        padded = np.pad(out, pad, mode="edge")
        cs = np.cumsum(padded, axis=axis)
        if axis == 0:
            out = (cs[2 * radius + 1:, :, :] - cs[:-(2 * radius + 1), :, :]) / (2 * radius + 1)
        else:
            out = (cs[:, 2 * radius + 1:, :] - cs[:, :-(2 * radius + 1), :]) / (2 * radius + 1)
    return out


def bilateral_lite(arr, radius=2, sigma_color=0.10):
    """Edge-aware smoothing: average neighbours whose colour is close to the centre.

    Implemented with box blurs of a similarity weight so memory stays flat.
    arr: float32 HxWx3 in 0..1
    """
    np = load_deps()[0]
    # local mean (guide)
    guide = box_blur(arr, radius)
    # similarity weight per pixel between centre and local mean
    diff = np.abs(arr - guide).mean(axis=2, keepdims=True)
    weight = np.exp(-(diff ** 2) / (2 * sigma_color ** 2))
    # weighted average of the neighbourhood, using the guide as the neighbour estimate
    num = guide * weight
    den = weight
    num = box_blur(num, radius)
    den = box_blur(den, radius)
    return num / np.clip(den, 1e-6, None)


def unsharp(arr, amount=0.2, radius=1):
    np = load_deps()[0]
    blurred = box_blur(arr, radius)
    return np.clip(arr + amount * (arr - blurred), 0.0, 1.0)


def process(path, strength, radius, sharpen, sigma_color, dry_run, np, Image):
    try:
        with Image.open(path) as im:
            mode = im.mode
            original_size = im.size
            arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    except Exception as exc:  # noqa: BLE001
        print(f"  {os.path.basename(path):<28} unreadable ({exc})")
        return False

    smoothed = bilateral_lite(arr, radius=radius, sigma_color=sigma_color)
    out = arr * (1.0 - strength) + smoothed * strength
    if sharpen > 0:
        out = unsharp(out, amount=sharpen, radius=1)
    out = np.clip(out, 0.0, 1.0)

    # measured change, as a sanity number
    delta = float(np.abs(out - arr).mean() * 255.0)
    print(f"  {os.path.basename(path):<28} {original_size[0]}x{original_size[1]}  "
          f"mean change {delta:4.2f}/255  {'(dry run)' if dry_run else ''}")
    if dry_run or delta < 0.05:
        return True

    img = Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), mode="RGB")
    if mode == "RGBA":
        alpha = Image.open(path).convert("RGBA").getchannel("A")
        img = img.convert("RGBA")
        img.putalpha(alpha)
    img.save(path, format="PNG", optimize=True)
    return True


def main(argv):
    ap = argparse.ArgumentParser(description="Low-memory denoise for Cycles renders.")
    ap.add_argument("paths", nargs="+", help="image files or directories")
    ap.add_argument("--strength", type=float, default=0.75)
    ap.add_argument("--radius", type=int, default=2)
    ap.add_argument("--sharpen", type=float, default=0.2)
    ap.add_argument("--sigma-color", type=float, default=0.10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    np, Image = load_deps()
    if np is None:
        return 2

    files: list[str] = []
    for p in args.paths:
        if os.path.isdir(p):
            files.extend(sorted(glob.glob(os.path.join(p, "*.png"))))
        else:
            files.extend(sorted(glob.glob(p)))
    files = [f for f in files if f.lower().endswith(".png")]
    if not files:
        print("no PNG files found")
        return 0

    print(f"denoising {len(files)} image(s)  strength={args.strength} radius={args.radius} "
          f"sharpen={args.sharpen}")
    ok = True
    for f in files:
        ok = process(f, args.strength, args.radius, args.sharpen,
                     args.sigma_color, args.dry_run, np, Image) and ok
    print("done" if ok else "finished with errors")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
