#!/usr/bin/env python3
"""preflight.py — local validator for the 3dmodels repository.

Run this BEFORE every push. A non-zero exit code means the package is not done.

Usage:
    python tools/preflight.py agent_atlas                     # validate a whole workspace
    python tools/preflight.py agent_atlas/my-first-model      # validate one package
    python tools/preflight.py --all                           # validate every workspace
    python tools/preflight.py --index                         # regenerate the root README index
    python tools/preflight.py agent_atlas --min-render 2000   # stricter render size
    python tools/preflight.py agent_atlas --strict            # treat warnings as failures

Checks (per package):
    layout        required files and folders exist with correct names
    naming        workspace/package/render file naming conventions
    renders       >= 5 PNGs, correct resolution, required views covered, no placeholder names
    archive       renders.zip opens, is flat, contains >= 5 images matching renders/
    readme        front-matter + all required sections, no TODO/TBD/placeholders,
                  render images embedded, limitations section present
    glb           valid container, geometry, materials, embedded textures, metric scale
    hygiene       forbidden files, file-size caps (60 MB file / 80 MB zip)

Stdlib only. Pillow and numpy are used if available for extra image checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from check_glb import analyse, load_any
except Exception:  # pragma: no cover - tool must still run standalone
    analyse = None
    load_any = None

# --------------------------------------------------------------------------- #
# Constants / rules
# --------------------------------------------------------------------------- #
MAX_FILE_MB = 60.0
MAX_ZIP_MB = 80.0
MIN_RENDERS = 5
MAX_RENDERS = 14
DEFAULT_MIN_RES = 1600

WORKSPACE_RE = re.compile(r"^agent_[a-z0-9]+(?:_[a-z0-9]+)*$")
PACKAGE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RENDER_RE = re.compile(r"^(\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.png$")

REQUIRED_VIEWS = {
    "hero": ("hero", "three-quarter", "threequarter"),
    "front": ("front",),
    "side": ("side", "left", "right"),
    "back": ("back", "rear"),
    "top": ("top", "bottom", "plan"),
    "detail": ("detail", "macro", "close"),
}

REQUIRED_SECTIONS = [
    "what this model depicts",
    "dimensions and scale",
    "technical sheet",
    "materials",
    "render set",
    "usage notes",
    "limitations",
    "self-review",
    "licence",
]

FORBIDDEN_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".env",
    "desktop.ini",
}
FORBIDDEN_SUFFIXES = {".blend1", ".blend2", ".exr", ".hdr", ".tmp", ".log", ".pyc"}
FORBIDDEN_DIRS = {"__pycache__", "node_modules", ".ipynb_checkpoints", "rejected", "render_cache"}

PLACEHOLDER_RE = re.compile(
    r"(?<![\w<])(TODO|TBD|FIXME|XXX|Lorem ipsum|PLACEHOLDER)(?![\w>])", re.IGNORECASE
)
# phrases that indicate an unfinished / abandoned package
UNFINISHED_RE = re.compile(
    r"(coming soon|to be added|will be added|next session|next run|work in progress"
    r"|\bWIP\b|placeholder render|not yet (modelled|rendered|written)|more renders later)",
    re.IGNORECASE,
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>\n]{0,60}>")


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def png_info(path: Path) -> tuple[int, int] | None:
    """Read width/height from a PNG IHDR without third-party libs."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(33)
        if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        if head[12:16] != b"IHDR":
            return None
        w, h = struct.unpack(">II", head[16:24])
        return w, h
    except OSError:
        return None


def human_mb(path: Path) -> float:
    try:
        return round(path.stat().st_size / (1024 * 1024), 2)
    except OSError:
        return 0.0


def parse_front_matter(text: str) -> dict[str, str] | None:
    """Parse a leading yaml-ish front-matter block, flat key: value pairs only."""
    lines = text.splitlines()
    if not lines:
        return None
    stripped = [ln.strip() for ln in lines]
    start = None
    for i, ln in enumerate(stripped[:10]):
        if ln == "---":
            start = i
            break
    if start is None:
        return None
    end = None
    for i in range(start + 1, len(stripped)):
        if stripped[i] == "---":
            end = i
            break
    if end is None:
        return None
    data: dict[str, str] = {}
    for ln in lines[start + 1 : end]:
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        data[k.strip()] = v.strip()
    return data


# --------------------------------------------------------------------------- #
# Package validation
# --------------------------------------------------------------------------- #
def validate_package(pkg_dir: Path, res: Result, min_res: int) -> None:
    name = pkg_dir.name
    if not PACKAGE_RE.match(name):
        res.err(f"package folder name '{name}' is not lowercase kebab-case")

    model_dir = pkg_dir / "model"
    renders_dir = pkg_dir / "renders"
    readme = pkg_dir / "README.md"
    zip_path = pkg_dir / "renders.zip"
    fm: dict[str, str] | None = None

    # ---------------- layout ----------------
    if not model_dir.is_dir():
        res.err("missing model/ directory")
    if not renders_dir.is_dir():
        res.err("missing renders/ directory")
    if not readme.is_file():
        res.err("missing README.md (copy templates/01_MODEL_README_TEMPLATE.md)")
    if not zip_path.is_file():
        res.err("missing renders.zip (required deliverable — the curated render archive)")

    glbs: list[Path] = []
    blends: list[Path] = []
    if model_dir.is_dir():
        glbs = sorted(model_dir.glob("*.glb")) + sorted(model_dir.glob("*.gltf"))
        blends = sorted(model_dir.glob("*.blend"))
        if not glbs:
            res.err("missing .glb export in model/ (the shippable mesh)")
        if not blends:
            res.err("missing .blend source in model/ (the editable source)")
        for p in glbs + blends:
            if p.stem != name:
                res.warn(f"{p.name} does not match package name '{name}' (rename it)")
            size = human_mb(p)
            if size > MAX_FILE_MB:
                res.err(f"{p.name} is {size} MB — exceeds the {MAX_FILE_MB:.0f} MB per-file cap")

    # ---------------- renders ----------------
    images: list[Path] = []
    if renders_dir.is_dir():
        images = sorted(p for p in renders_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png")
        other = [
            p.name
            for p in renders_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".exr"}
        ]
        if other:
            res.err(f"renders/ contains non-PNG images ({', '.join(other[:4])}) — hero renders must be PNG")

        if len(images) < MIN_RENDERS:
            res.err(
                f"only {len(images)} render(s) in renders/ — at least {MIN_RENDERS} required "
                "(hero 3/4, front, side, back, top/bottom, + detail or wireframe)"
            )
        if len(images) > MAX_RENDERS:
            res.warn(f"{len(images)} renders — more than {MAX_RENDERS} is clutter; curate the best set")

        view_hits: set[str] = set()
        for img in images:
            if not RENDER_RE.match(img.name):
                res.err(
                    f"render '{img.name}' must match NN-kebab-description.png "
                    "(e.g. 01-hero-three-quarter.png)"
                )
            info = png_info(img)
            if info is None:
                res.err(f"'{img.name}' is not a readable PNG")
            else:
                w, h = info
                if min(w, h) < min_res:
                    res.err(f"'{img.name}' is {w}x{h} — minimum is {min_res}x{min_res}")
                if abs(w - h) > 2:
                    res.warn(f"'{img.name}' is {w}x{h} — renders should be square")
                for view, keys in REQUIRED_VIEWS.items():
                    if any(k in img.name.lower() for k in keys):
                        view_hits.add(view)
            size = human_mb(img)
            if size > MAX_FILE_MB:
                res.err(f"'{img.name}' is {size} MB — exceeds the {MAX_FILE_MB:.0f} MB per-file cap")

        missing_views = [
            v for v in ("hero", "front", "side", "back")
            if v not in view_hits
        ]
        if missing_views:
            res.err(
                "render set is missing required views: "
                + ", ".join(missing_views)
                + " (name files e.g. 02-front.png, 03-side.png, 04-back.png)"
            )
        if "top" not in view_hits:
            res.warn("no top/bottom view found (required by docs/RENDER_SPEC.md)")
        if "detail" not in view_hits:
            res.warn("no detail/macro view found (required by docs/RENDER_SPEC.md)")
        res.note(f"renders: {len(images)} PNG, views covered: {', '.join(sorted(view_hits)) or 'none'}")

    # ---------------- archive ----------------
    if zip_path.is_file():
        size = human_mb(zip_path)
        if size > MAX_ZIP_MB:
            res.err(f"renders.zip is {size} MB — exceeds the {MAX_ZIP_MB:.0f} MB cap")
        try:
            with zipfile.ZipFile(zip_path) as zf:
                bad = zf.testzip()
                if bad is not None:
                    res.err(f"renders.zip is corrupt (first bad member: {bad})")
                names = [n for n in zf.namelist() if not n.endswith("/")]
                imgs = [n for n in names if n.lower().endswith(".png")]
                if len(imgs) < MIN_RENDERS:
                    res.err(f"renders.zip contains {len(imgs)} PNG(s) — at least {MIN_RENDERS} required")
                nested = [n for n in imgs if "/" in n]
                if nested:
                    res.err(
                        "renders.zip must be a flat archive of images; found nested paths such as "
                        f"'{nested[0]}' (build it with: zip -j renders.zip renders/*.png)"
                    )
                junk = [n for n in names if not n.lower().endswith(".png")]
                if junk:
                    res.warn(f"renders.zip contains {len(junk)} non-PNG entry/entries, e.g. '{junk[0]}'")
                if images:
                    disk = {p.name for p in images}
                    zip_names = {os.path.basename(n) for n in imgs}
                    missing_in_zip = disk - zip_names
                    extra_in_zip = zip_names - disk
                    if missing_in_zip:
                        res.err(
                            "renders.zip is out of sync with renders/ — missing: "
                            + ", ".join(sorted(missing_in_zip)[:5])
                        )
                    if extra_in_zip:
                        res.err(
                            "renders.zip contains images not present in renders/: "
                            + ", ".join(sorted(extra_in_zip)[:5])
                        )
                kind = "nested" if any("/" in n for n in imgs) else "flat"
                if images:
                    newest = max(p.stat().st_mtime for p in images)
                    if zip_path.stat().st_mtime + 1 < newest:
                        res.err(
                            "renders.zip is older than the newest file in renders/ — "
                            "you edited renders but did not rebuild the archive"
                        )
                res.note(f"renders.zip: {len(imgs)} image(s), {size} MB, {kind} archive")
        except zipfile.BadZipFile:
            res.err("renders.zip is not a valid zip archive")

    # ---------------- README ----------------
    if readme.is_file():
        text = readme.read_text(encoding="utf-8", errors="replace")
        fm = parse_front_matter(text)
        if fm is None:
            res.err("README.md is missing a fenced front-matter block (--- ... ---) with package metadata")
        else:
            required_fm = ["model", "category", "dimensions_m", "triangles", "status", "license"]
            missing = [k for k in required_fm if k not in fm]
            if missing:
                res.err("README front-matter is missing keys: " + ", ".join(missing))
            status = fm.get("status", "").strip().strip("'\"")
            if status and status not in {"draft", "in-review", "released", "deprecated"}:
                res.warn(f"front-matter status '{status}' is not one of draft|in-review|released|deprecated")
            if status == "draft":
                res.err(
                    "front-matter status is 'draft' — a pushed package must be 'released'. "
                    "Do not push half-finished packages (docs/NO_STOPPING.md)."
                )
            if status == "deprecated":
                res.warn("front-matter status is 'deprecated'")

        low = text.lower()
        missing_sections = [s for s in REQUIRED_SECTIONS if s not in low]
        if missing_sections:
            res.err("README.md is missing required section(s): " + ", ".join(missing_sections))

        hits = PLACEHOLDER_RE.findall(text)
        if hits:
            res.err("README.md still contains placeholder markers: " + ", ".join(sorted(set(hits))))
        unfinished = UNFINISHED_RE.findall(text)
        if unfinished:
            res.err(
                "README.md contains language that indicates an unfinished package: "
                + ", ".join(sorted({(u[0] if isinstance(u, tuple) else u).lower() for u in unfinished}))
                + ". Finish it (docs/NO_STOPPING.md)."
            )
        angles = ANGLE_PLACEHOLDER_RE.findall(text)
        if angles:
            res.err(
                "README.md still contains <angle-bracket> template placeholders, e.g. "
                + ", ".join(angles[:5])
            )

        if "renders/" not in text:
            res.err("README.md does not embed any render (expected markdown paths like renders/01-hero-three-quarter.png)")
        else:
            embedded = set(re.findall(r"renders/([A-Za-z0-9._-]+\.png)", text))
            if images:
                on_disk = {p.name for p in images}
                absent = embedded - on_disk
                if absent:
                    res.err("README.md references renders that do not exist: " + ", ".join(sorted(absent)))
                if len(embedded) < min(4, len(on_disk)):
                    res.warn(f"README.md embeds only {len(embedded)} render(s); embed the whole set")

        if len(text) < 1500:
            res.err(f"README.md is only {len(text)} characters — too thin; see docs/MODEL_SPEC.md")

        lim_idx = low.find("limitations")
        if lim_idx >= 0:
            tail = text[lim_idx : lim_idx + 900]
            bullets = len(re.findall(r"^\s*[-*]\s+\S", tail, re.MULTILINE))
            if bullets < 2:
                res.err("Limitations section has fewer than 2 concrete items — be honest about gaps")

    # ---------------- glb ----------------
    if glbs and load_any is not None and analyse is not None:
        for g in glbs:
            try:
                report = analyse(load_any(str(g)), str(g))
            except Exception as exc:  # noqa: BLE001
                res.err(f"{g.name} could not be parsed: {exc}")
                continue
            for check in report.get("checks", []):
                if not check["ok"]:
                    target = res.err if check["level"] == "fail" else res.warn
                    target(f"GLB {g.name}: {check['message']}")
            res.note(
                f"GLB {g.name}: {report['triangles']} tris, {report['materials']} materials, "
                f"{report['images']} embedded image(s), "
                f"{(report['bbox'] or {}).get('dims_label', 'no bounds')}"
            )
            if fm is not None and fm.get("triangles"):
                declared = re.sub(r"[^0-9]", "", fm["triangles"])
                if declared.isdigit() and report["triangles"]:
                    delta = abs(int(declared) - report["triangles"]) / max(report["triangles"], 1)
                    if delta > 0.15:
                        res.warn(
                            f"README declares {declared} triangles but the GLB has {report['triangles']} "
                            f"({delta*100:.0f}% off) — keep the front-matter accurate"
                        )

    # ---------------- brief linkage (informational) ----------------
    briefs_root = HERE.parent / "BRIEFS"
    if briefs_root.is_dir():
        claimed = list((briefs_root / "CLAIMED").glob(f"*{name}.md")) \
            if (briefs_root / "CLAIMED").is_dir() else []
        delivered = list((briefs_root / "DELIVERED").glob(f"*{name}.md")) \
            if (briefs_root / "DELIVERED").is_dir() else []
        if claimed:
            res.note(f"brief: {claimed[0].name} is still in BRIEFS/CLAIMED — "
                     f"run: python tools/claim_brief.py --deliver <id> once this is pushed")
            brief_text = claimed[0].read_text(encoding="utf-8", errors="replace")
            must = []
            in_must = False
            for line in brief_text.splitlines():
                if line.startswith("must_have:"):
                    in_must = True
                    continue
                if in_must:
                    if line.startswith("  - "):
                        must.append(line[4:].strip().strip('"').strip("'"))
                    elif line and not line.startswith((" ", "\t", "-")):
                        in_must = False
            readme_low = (readme.read_text(encoding="utf-8", errors="replace").lower()
                          if readme.is_file() else "")
            absent = [m for m in must
                      if readme_low and not any(w in readme_low
                                                for w in m.lower().split() if len(w) > 4)]
            if absent:
                res.warn(
                    "brief must_have item(s) not mentioned in this package's README — "
                    "did you build what was asked? "
                    + "; ".join(a[:60] for a in absent[:3])
                )
        elif delivered:
            res.note(f"brief: {delivered[0].name} delivered")
        else:
            res.warn("no matching brief in BRIEFS/CLAIMED or BRIEFS/DELIVERED — "
                     "this package was not built from an owner brief "
                     "(allowed, but the brief queue is the preferred path: BRIEFS.md)")

    # ---------------- hygiene ----------------
    for p in pkg_dir.rglob("*"):
        parts = set(p.relative_to(pkg_dir).parts)
        if p.name in FORBIDDEN_FILES:
            res.err(f"forbidden file committed: {p.relative_to(pkg_dir)}")
        if p.suffix.lower() in FORBIDDEN_SUFFIXES:
            res.err(f"forbidden file type committed: {p.relative_to(pkg_dir)}")
        if parts & FORBIDDEN_DIRS:
            res.err(f"forbidden directory committed: {next(iter(parts & FORBIDDEN_DIRS))}/")
        if p.is_file() and human_mb(p) > MAX_FILE_MB:
            res.err(f"{p.relative_to(pkg_dir)} is {human_mb(p)} MB — exceeds the {MAX_FILE_MB:.0f} MB cap")


# --------------------------------------------------------------------------- #
# Workspace validation
# --------------------------------------------------------------------------- #
def validate_workspace(ws: Path, min_res: int, strict: bool = False) -> list[Result]:
    root = Result(path=str(ws))
    if not WORKSPACE_RE.match(ws.name):
        root.err(
            f"workspace folder '{ws.name}' must be named agent_<slug> using lowercase letters, "
            "digits and single underscores (e.g. agent_atlas)"
        )

    roadmap = ws / "ROADMAP.md"
    if not roadmap.is_file():
        root.err("missing ROADMAP.md in the workspace root (copy templates/02_ROADMAP_TEMPLATE.md)")
    else:
        rtext = roadmap.read_text(encoding="utf-8", errors="replace")
        if PLACEHOLDER_RE.search(rtext):
            root.warn("ROADMAP.md still contains TODO/TBD markers")
        if ANGLE_PLACEHOLDER_RE.search(rtext):
            root.warn("ROADMAP.md still contains <angle-bracket> placeholders")

    packages = [
        p for p in sorted(ws.iterdir())
        if p.is_dir() and not p.name.startswith(".") and p.name not in FORBIDDEN_DIRS
    ]
    if not packages:
        root.err("workspace contains no model package subfolder (agent_<slug>/<model-name>/)")

    results = [root]
    for pkg in packages:
        r = Result(path=str(pkg))
        validate_package(pkg, r, min_res)
        if strict:
            r.errors.extend(f"(strict) {w}" for w in r.warnings)
            r.warnings.clear()
        results.append(r)
    return results


def discover(targets: list[str]) -> list[Path]:
    if not targets:
        targets = ["."]
    found: list[Path] = []
    for t in targets:
        p = Path(t).resolve()
        if p.is_dir():
            if WORKSPACE_RE.match(p.name):
                found.append(p)
            else:
                found.extend(
                    sorted(
                        c for c in p.iterdir() if c.is_dir() and WORKSPACE_RE.match(c.name)
                    )
                )
        else:
            raise SystemExit(f"error: not a directory: {t}")
    return found


# --------------------------------------------------------------------------- #
# Index generation
# --------------------------------------------------------------------------- #
def regenerate_index(repo_root: Path) -> None:
    readme = repo_root / "README.md"
    if not readme.is_file():
        raise SystemExit("error: run --index from the repository root (README.md not found)")
    rows = []
    for ws in sorted(repo_root.glob("agent_*")):
        if not ws.is_dir():
            continue
        for pkg in sorted(p for p in ws.iterdir() if p.is_dir() and not p.name.startswith(".")):
            fm = {}
            rp = pkg / "README.md"
            if rp.is_file():
                fm = parse_front_matter(rp.read_text(encoding="utf-8", errors="replace")) or {}
            n_renders = len(list((pkg / "renders").glob("*.png"))) if (pkg / "renders").is_dir() else 0
            category = (fm.get("category") or "—").strip("'\"")
            rows.append(
                f"| [{pkg.name}]({ws.name}/{pkg.name}/) | {category} | `{ws.name}` | "
                f"`{pkg.name}` | {n_renders} |"
            )
    body = ["| Model | Category | Workspace | Package | Renders |", "| --- | --- | --- | --- | --- |"]
    body += rows or ["| _no models yet_ | | | | |"]
    text = readme.read_text(encoding="utf-8")
    block = "\n".join(body)
    new = re.sub(
        r"<!-- MODELS:START -->.*?<!-- MODELS:END -->",
        f"<!-- MODELS:START -->\n{block}\n<!-- MODELS:END -->",
        text,
        flags=re.DOTALL,
    )
    readme.write_text(new, encoding="utf-8")
    print(f"index regenerated: {len(rows)} package(s)")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Validate 3dmodels agent workspaces and model packages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("paths", nargs="*", help="workspace or package directories")
    ap.add_argument("--all", action="store_true", help="validate every agent_* workspace under cwd")
    ap.add_argument("--index", action="store_true", help="regenerate the model index in README.md")
    ap.add_argument("--min-render", type=int, default=DEFAULT_MIN_RES, help="minimum render size in px")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--json", action="store_true", help="emit JSON results")
    args = ap.parse_args(argv)

    repo_root = HERE.parent
    if args.index:
        regenerate_index(repo_root)
        return 0

    targets = discover(args.paths)
    if not targets:
        print("error: no agent_* workspace found to validate", file=sys.stderr)
        print("hint: workspaces must be named agent_<slug> at the repository root", file=sys.stderr)
        return 2

    all_results: list[Result] = []
    for ws in targets:
        # a package path was given directly
        if (ws / "README.md").is_file() and (ws / "model").is_dir() and not (ws / "ROADMAP.md").exists():
            r = Result(path=str(ws))
            validate_package(ws, r, args.min_render)
            if args.strict:
                r.errors.extend(f"(strict) {w}" for w in r.warnings)
                r.warnings.clear()
            all_results.append(r)
        else:
            all_results.extend(validate_workspace(ws, args.min_render, args.strict))

    if args.json:
        print(
            json.dumps(
                [
                    {"path": r.path, "ok": r.ok, "errors": r.errors, "warnings": r.warnings, "notes": r.notes}
                    for r in all_results
                ],
                indent=2,
            )
        )
        return 0 if all(r.ok for r in all_results) else 1

    total_err = total_warn = 0
    for r in all_results:
        rel = os.path.relpath(r.path, Path.cwd())
        status = "OK  " if r.ok else "FAIL"
        print(f"\n[{status}] {rel}")
        for e in r.errors:
            print(f"   ✗ {e}")
        for w in r.warnings:
            print(f"   ! {w}")
        for n in r.notes:
            print(f"   · {n}")
        total_err += len(r.errors)
        total_warn += len(r.warnings)

    print("\n" + "=" * 68)
    if total_err:
        print(f"PREFLIGHT FAILED — {total_err} error(s), {total_warn} warning(s).")
        print("Fix the errors above. Do not push until this exits 0.")
        print("See AGENTS.md §3 (Definition of Done) for what each check means.")
        return 1
    if total_warn:
        print(f"PREFLIGHT PASSED with {total_warn} warning(s). Review them before pushing.")
    else:
        print("PREFLIGHT PASSED — clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
