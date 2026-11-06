#!/usr/bin/env python3
"""make_render_sheet.py — build a contact sheet of a package's renders.

The contact sheet is a review aid: looking at every render at once exposes inconsistent
exposure, framing drift, and weak silhouettes that are easy to miss image by image.
It is a working file, NOT a deliverable — do not commit it (it is git-ignored).

Usage:
    python tools/make_render_sheet.py agent_atlas/my-first-model
    python tools/make_render_sheet.py agent_atlas/my-first-model --cols 3 --thumb 640

Output:
    <package>/contact-sheet.jpg   when Pillow is available
    <package>/contact-sheet.html  always (open it in a browser/preview)

Stdlib fallback: the HTML sheet embeds the images directly, so it works with no dependencies.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None


def find_package(path: Path) -> Path:
    if (path / "renders").is_dir():
        return path
    candidates = [p for p in sorted(path.iterdir()) if (p / "renders").is_dir()] if path.is_dir() else []
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"error: no package with a renders/ folder found in {path}")
    raise SystemExit(
        "error: multiple packages found; pass one explicitly:\n  "
        + "\n  ".join(str(c) for c in candidates)
    )


def make_with_pillow(images: list[Path], out: Path, cols: int, thumb: int) -> None:
    rows = (len(images) + cols - 1) // cols
    label_h = 28
    pad = 12
    sheet_w = cols * thumb + pad * (cols + 1)
    sheet_h = rows * (thumb + label_h) + pad * (rows + 1)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (24, 24, 27))
    draw = ImageDraw.Draw(sheet)

    for i, img_path in enumerate(images):
        r, c = divmod(i, cols)
        x = pad + c * (thumb + pad)
        y = pad + r * (thumb + label_h + pad)
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb, thumb), Image.LANCZOS)
                sheet.paste(im, (x + (thumb - im.width) // 2, y + (thumb - im.height) // 2))
                w, h = im.size
                caption = f"{img_path.name}  ({w}x{h})"
        except Exception as exc:  # noqa: BLE001
            caption = f"{img_path.name} — unreadable ({exc})"
        draw.text((x + 2, y + thumb + 6), caption[:70], fill=(210, 210, 215))

    sheet.save(out, quality=92)
    print(f"wrote {out}  ({len(images)} images, {cols} cols)")


def make_html(images: list[Path], out: Path, cols: int) -> None:
    cells = []
    for img in images:
        src = html.escape(f"renders/{img.name}")
        cells.append(
            f'<figure><img src="{src}" alt="{html.escape(img.name)}">'
            f"<figcaption>{html.escape(img.name)}</figcaption></figure>"
        )
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Render review sheet — {html.escape(out.parent.name)}</title>
<style>
  body {{ margin:0; padding:24px; background:#141417; color:#e7e7ea;
         font:14px/1.4 ui-sans-serif, system-ui, sans-serif; }}
  h1 {{ font-size:16px; font-weight:600; margin:0 0 16px; }}
  .grid {{ display:grid; gap:16px; grid-template-columns:repeat({cols}, minmax(0,1fr)); }}
  figure {{ margin:0; background:#1c1c20; border-radius:8px; overflow:hidden; }}
  img {{ width:100%; display:block; }}
  figcaption {{ padding:8px 10px; font-size:12px; color:#a9a9b3;
                font-family:ui-monospace, monospace; }}
</style>
</head>
<body>
<h1>Render review sheet — {html.escape(out.parent.name)} ({len(images)} images)</h1>
<div class="grid">
{chr(10).join(cells)}
</div>
</body>
</html>
"""
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out}  ({len(images)} images, open in a browser)")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build a contact sheet of a package's renders.")
    ap.add_argument("path", help="package directory (or a workspace with exactly one package)")
    ap.add_argument("--cols", type=int, default=3, help="columns in the sheet (default 3)")
    ap.add_argument("--thumb", type=int, default=560, help="thumbnail size in px (default 560)")
    ap.add_argument("--html-only", action="store_true", help="skip the JPEG and write only HTML")
    args = ap.parse_args(argv)

    pkg = find_package(Path(args.path).resolve())
    renders = pkg / "renders"
    images = sorted(p for p in renders.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not images:
        print(f"error: no images in {renders}", file=sys.stderr)
        return 1

    if args.cols < 1:
        args.cols = 1

    if Image is not None and not args.html_only:
        make_with_pillow(images, pkg / "contact-sheet.jpg", args.cols, args.thumb)
    else:
        if not args.html_only:
            print("note: Pillow not installed — writing the HTML sheet instead "
                  "(pip install pillow for a JPEG sheet)")
    make_html(images, pkg / "contact-sheet.html", args.cols)

    print("\nInspect this sheet before pushing. Look for: clipped extremities, framing drift,")
    print("inconsistent exposure, flat lighting, noisy shadows, texture seams, floating parts.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
