#!/usr/bin/env python3
"""check_glb.py — inspect a GLB/glTF file and report whether it meets repo standards.

Stdlib only (numpy optional, unused). Usage:

    python tools/check_glb.py path/to/model.glb [--json] [--max-tris 500000]

Exit codes: 0 = all checks pass, 1 = one or more checks failed, 2 = file unreadable.

Checks performed:
  * GLB container / JSON chunk parse
  * at least one mesh with geometry
  * triangle count within a (configurable) budget
  * materials present, PBR metallic-roughness, no pure black/white base colours
  * normals present on all primitives
  * images embedded (a package must be self-contained)
  * bounding box reported in metres, with a scale sanity warning
  * up-axis note (glTF spec is +Y up)
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

GLB_MAGIC = 0x46546C67  # "glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_glb(path: str) -> dict:
    """Parse a binary GLB and return the glTF JSON dict."""
    with open(path, "rb") as fh:
        data = fh.read()

    if len(data) < 12:
        raise ValueError("file too small to be a GLB")

    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise ValueError("not a GLB file (bad magic); for .gltf JSON use load_gltf()")
    if version != 2:
        raise ValueError(f"unsupported GLB version {version} (expected 2)")
    if length != len(data):
        raise ValueError(f"declared length {length} != actual size {len(data)}")

    offset = 12
    gltf = None
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8 : offset + 8 + chunk_len]
        offset += 8 + chunk_len + ((4 - chunk_len % 4) % 4 if chunk_len % 4 else 0)
        if chunk_type == CHUNK_JSON:
            gltf = json.loads(chunk.decode("utf-8").rstrip("\x00 ").strip())
        elif chunk_type == CHUNK_BIN:
            pass
    if gltf is None:
        raise ValueError("no JSON chunk found in GLB")
    return gltf


def load_gltf(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_any(path: str) -> dict:
    return load_gltf(path) if path.lower().endswith(".gltf") else load_glb(path)


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def srgb(c) -> float:
    """Linear -> approximate sRGB for reporting only."""
    c = max(0.0, min(1.0, float(c)))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def analyse(gltf: dict, path: str) -> dict:
    report: dict = {
        "file": os.path.basename(path),
        "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        "meshes": len(gltf.get("meshes", [])),
        "nodes": len(gltf.get("nodes", [])),
        "materials": len(gltf.get("materials", [])),
        "textures": len(gltf.get("textures", [])),
        "images": len(gltf.get("images", [])),
        "animations": len(gltf.get("animations", [])),
        "skins": len(gltf.get("skins", [])),
        "triangles": 0,
        "primitives": 0,
        "primitives_without_normals": 0,
        "degenerate_primitives": 0,
        "bbox": None,
        "materials_report": [],
        "images_embedded": 0,
        "generator": gltf.get("asset", {}).get("generator", "unknown"),
        "checks": [],
    }

    accessors = gltf.get("accessors", [])
    mins, maxs = [], []

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            report["primitives"] += 1
            attrs = prim.get("attributes", {})
            if "NORMAL" not in attrs:
                report["primitives_without_normals"] += 1

            idx = prim.get("indices")
            if idx is not None:
                acc = accessors[idx]
                count = acc.get("count", 0)
                report["triangles"] += count // 3
                if count == 0:
                    report["degenerate_primitives"] += 1
            elif "POSITION" in attrs:
                acc = accessors[attrs["POSITION"]]
                report["triangles"] += acc.get("count", 0) // 3

            pos = attrs.get("POSITION")
            if pos is not None:
                acc = accessors[pos]
                if "min" in acc and "max" in acc and len(acc["min"]) >= 3:
                    mins.append(acc["min"])
                    maxs.append(acc["max"])

    if mins and maxs:
        lo = [min(m[i] for m in mins) for i in range(3)]
        hi = [max(m[i] for m in maxs) for i in range(3)]
        dims = [round(hi[i] - lo[i], 4) for i in range(3)]
        report["bbox"] = {
            "min": [round(v, 4) for v in lo],
            "max": [round(v, 4) for v in hi],
            "dims_xyz": dims,
            "dims_label": f"X {dims[0]} m × Y {dims[1]} m × Z {dims[2]} m (glTF: Y up)",
            "largest_dim_m": max(dims),
        }

    for mat in gltf.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {}) or {}
        base = pbr.get("baseColorFactor", [1, 1, 1, 1])
        hexcol = "#%02X%02X%02X" % tuple(int(round(srgb(c) * 255)) for c in base[:3])
        entry = {
            "name": mat.get("name", "<unnamed>"),
            "base_color_srgb": hexcol,
            "metallic": pbr.get("metallicFactor", 1.0),
            "roughness": pbr.get("roughnessFactor", 1.0),
            "has_basecolor_texture": "baseColorTexture" in pbr,
            "has_mr_texture": "metallicRoughnessTexture" in pbr,
            "has_normal_texture": "normalTexture" in mat,
            "double_sided": mat.get("doubleSided", False),
            "emissive": mat.get("emissiveFactor", [0, 0, 0]),
        }
        report["materials_report"].append(entry)

    report["images_embedded"] = sum(
        1 for img in gltf.get("images", []) if "bufferView" in img or str(img.get("uri", "")).startswith("data:")
    )

    # -------- checks -------- #
    checks: list[dict] = []

    def add(ok: bool, level: str, msg: str) -> None:
        checks.append({"ok": ok, "level": level, "message": msg})

    add(report["primitives"] > 0, "fail", f"{report['primitives']} mesh primitive(s) found")
    add(report["triangles"] > 0, "fail", f"{report['triangles']} triangles")
    add(
        report["primitives_without_normals"] == 0,
        "fail",
        f"{report['primitives_without_normals']} primitive(s) missing NORMAL attribute",
    )
    add(report["materials"] > 0, "fail", f"{report['materials']} material(s)")

    bad_colour = [
        m for m in report["materials_report"]
        if m["base_color_srgb"] in ("#FFFFFF", "#000000") and not m["has_basecolor_texture"]
    ]
    add(
        not bad_colour,
        "fail",
        "materials with pure white/black base colour: "
        + (", ".join(m["name"] for m in bad_colour) if bad_colour else "none"),
    )

    unnamed = [m["name"] for m in report["materials_report"] if m["name"] == "<unnamed>"]
    add(not unnamed, "warn", f"{len(unnamed)} unnamed material(s)")

    if report["images"]:
        add(
            report["images_embedded"] == report["images"],
            "fail",
            f"{report['images_embedded']}/{report['images']} image(s) embedded in the GLB "
            "(package must be self-contained)",
        )

    if report["bbox"]:
        largest = report["bbox"]["largest_dim_m"]
        add(
            0.001 <= largest <= 1000.0,
            "warn",
            f"largest dimension {largest} m — check that the model is at real-world metric scale",
        )
        lo = report["bbox"]["min"][1]
        add(
            -0.2 <= lo <= 1.0,
            "warn",
            f"bounding box min Y = {lo} — expected roughly 0 for a model sitting on the ground "
            "(glTF is Y-up: offset from 0 suggests unapplied transforms or a misplaced origin)",
        )

    report["checks"] = checks
    report["ok"] = all(c["ok"] for c in checks if c["level"] == "fail")
    return report


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Inspect a GLB/glTF against repo standards.")
    ap.add_argument("file", help="path to .glb or .gltf")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--max-tris", type=int, default=None, help="fail if triangle count exceeds this")
    ap.add_argument("--max-mb", type=float, default=60.0, help="fail if file exceeds this size (MB)")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.file):
        print(f"error: no such file: {args.file}", file=sys.stderr)
        return 2

    try:
        gltf = load_any(args.file)
    except Exception as exc:  # noqa: BLE001 - report any parse failure plainly
        print(f"error: could not parse {args.file}: {exc}", file=sys.stderr)
        return 2

    rep = analyse(gltf, args.file)
    extra_fail = False
    if args.max_tris is not None and rep["triangles"] > args.max_tris:
        rep["checks"].append(
            {"ok": False, "level": "fail",
             "message": f"triangle count {rep['triangles']} exceeds budget {args.max_tris}"}
        )
        extra_fail = True
    if rep["size_mb"] > args.max_mb:
        rep["checks"].append(
            {"ok": False, "level": "fail",
             "message": f"file size {rep['size_mb']} MB exceeds limit {args.max_mb} MB"}
        )
        extra_fail = True
    rep["ok"] = rep["ok"] and not extra_fail

    if args.json:
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1

    print(f"\n=== GLB report: {rep['file']} ===")
    print(f"generator      : {rep['generator']}")
    print(f"size           : {rep['size_mb']} MB")
    print(f"nodes/meshes   : {rep['nodes']} nodes, {rep['meshes']} meshes, {rep['primitives']} primitives")
    print(f"triangles      : {rep['triangles']}")
    print(f"materials      : {rep['materials']}   textures: {rep['textures']}   images: {rep['images']}")
    if rep["animations"] or rep["skins"]:
        print(f"rig            : {rep['skins']} skin(s), {rep['animations']} animation(s)")
    if rep["bbox"]:
        print(f"bounding box   : {rep['bbox']['dims_label']}")
        print(f"  min/max      : {rep['bbox']['min']} / {rep['bbox']['max']}")
    if rep["materials_report"]:
        print("\nmaterials:")
        for m in rep["materials_report"]:
            flags = "".join(
                [
                    "C" if m["has_basecolor_texture"] else "-",
                    "M" if m["has_mr_texture"] else "-",
                    "N" if m["has_normal_texture"] else "-",
                ]
            )
            print(
                f"  {m['name']:<32} {m['base_color_srgb']}  rough {m['roughness']:.2f}  "
                f"metal {m['metallic']:.2f}  [{flags}]"
            )
    print("\nchecks:")
    for c in rep["checks"]:
        mark = "PASS" if c["ok"] else ("FAIL" if c["level"] == "fail" else "WARN")
        print(f"  [{mark}] {c['message']}")

    print("\nRESULT:", "OK" if rep["ok"] else "FAILED")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
