#!/usr/bin/env python3
"""brief_from_pack.py — generate owner-style briefs from a themed pack file.

A pack is a YAML file listing subjects. This tool turns the next N unused items into normal
briefs in BRIEFS/OPEN/, so an agent's claim workflow never changes.

Usage
-----
    python tools/brief_from_pack.py packs/basic-props.pack --list
    python tools/brief_from_pack.py packs/basic-props.pack --count 3
    python tools/brief_from_pack.py packs/basic-props.pack --count 1 --dry-run

How "already generated" is tracked
    Generated briefs carry `pack: <name>` and `pack_item: <slug>` in their front-matter.
    Any item whose slug already appears in OPEN/, CLAIMED/ or DELIVERED/ is skipped, so you can
    call this repeatedly (once per agent) without creating duplicates.

Exit codes: 0 = ok, 1 = nothing left to generate, 2 = usage/parse error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRIEFS = REPO / "BRIEFS"

REQUIRED_ITEM_FIELDS = ("slug", "title")
DEFAULT_ITEM = {
    "category": "hard-surface-prop",
    "style": "stylised-realistic",
    "tri_budget": "15000-60000",
    "min_renders": 5,
    "min_render_px": 1600,
    "deliverables": "[glb, blend, renders, zip, readme]",
}


# --------------------------------------------------------------------------- #
# minimal YAML reader (no PyYAML dependency)
# --------------------------------------------------------------------------- #
def parse_pack(text: str) -> dict:
    """Parse the subset of YAML used by .pack files.

    Supported: top-level scalars, one level of nested mapping (`defaults:`), and a list of
    mappings under `items:` where each item's values may be scalars or inline lists
    (`[a, b, c]`) or multi-line block lists (`- a` lines under the key).
    """
    pack: dict = {"defaults": {}, "items": []}
    section = None
    current: dict | None = None
    list_key: str | None = None
    block_key: str | None = None      # collecting a folded/literal block scalar
    block_indent: int | None = None

    for raw in text.splitlines():
        # a block scalar swallows every indented line until dedent
        if block_key is not None:
            indent_now = len(raw) - len(raw.lstrip()) if raw.strip() else block_indent
            if not raw.strip() or (block_indent is not None and indent_now >= block_indent):
                target = current if current is not None else pack
                target[block_key] = (target.get(block_key, "") + " " + raw.strip()).strip()
                continue
            block_key, block_indent = None, None

        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if indent == 0 and not line.startswith("-"):
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key == "items":
                section = "items"
                continue
            if key == "defaults":
                section = "defaults"
                continue
            section = None
            pack[key] = value
            continue

        if section == "defaults":
            key, _, value = line.partition(":")
            pack["defaults"][key.strip()] = value.strip()
            continue

        if section == "items":
            if line.startswith("- "):
                content = line[2:].strip()
                if ":" in content and not content.startswith("["):
                    key, _, value = content.partition(":")
                    current = {key.strip(): value.strip()}
                    pack["items"].append(current)
                    list_key = None
                    if value.strip() in (">", "|", ">-", "|-"):
                        block_key = key.strip()
                        block_indent = None
                        current[block_key] = ""
                else:
                    # a bare "- value" continuation of the previous block list
                    if current is not None and list_key:
                        current.setdefault(f"__list__{list_key}", []).append(content)
                continue

            if current is None:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key, value = key.strip(), value.strip()
                if value in (">", "|", ">-", "|-"):
                    block_key = key
                    block_indent = indent + 2
                    current[key] = ""
                    list_key = None
                elif value == "":
                    list_key = key
                    current[f"__list__{key}"] = []
                else:
                    current[key] = value
                    list_key = None
            elif list_key:
                current[f"__list__{list_key}"].append(line.lstrip("- ").strip())
    return pack


def as_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    v = str(value).strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
    return [v]


# --------------------------------------------------------------------------- #
# generation
# --------------------------------------------------------------------------- #
def used_slugs() -> set[str]:
    slugs: set[str] = set()
    for folder in ("OPEN", "CLAIMED", "DELIVERED"):
        for p in (BRIEFS / folder).glob("*.md"):
            m = re.match(r"^\d{4}-(.+)\.md$", p.name)
            if m:
                slugs.add(m.group(1))
            text = p.read_text(encoding="utf-8", errors="replace")
            for field in ("slug:", "pack_item:"):
                for line in text.splitlines():
                    if line.strip().startswith(field):
                        slugs.add(line.split(":", 1)[1].strip().strip('"').strip("'"))
    return slugs


def next_number() -> int:
    nums = []
    for folder in ("OPEN", "CLAIMED", "DELIVERED"):
        for p in (BRIEFS / folder).glob("*.md"):
            m = re.match(r"^(\d{4})-", p.name)
            if m:
                nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def build_brief(pack_name: str, pack: dict, item: dict, number: int) -> str:
    defaults = {**DEFAULT_ITEM, **pack.get("defaults", {})}
    get = lambda k: item.get(k, defaults.get(k, pack.get(k, "")))  # noqa: E731

    slug = item["slug"].strip()
    title = item["title"].strip()
    must = as_list(item.get("__list__must_have") or item.get("must_have"))
    avoid = as_list(item.get("__list__avoid") or item.get("avoid"))
    accept = as_list(item.get("__list__acceptance") or item.get("acceptance"))
    refs = as_list(item.get("__list__references") or item.get("references"))
    parts = as_list(item.get("__list__parts") or item.get("parts"))

    lines = [
        "---",
        f'id: "{number:04d}"',
        f"slug: {slug}",
        f"title: {title}",
        f"category: {get('category')}",
        "priority: normal",
        "status: open",
        f"style: {get('style')}",
        f"origin: pack",
        f"pack: {pack_name}",
        f"pack_item: {slug}",
        f"dimensions_m: {item.get('dimensions_m', '{x: 0.000, y: 0.000, z: 0.000}')}",
        f"tri_budget: {get('tri_budget')}",
        f"deliverables: {get('deliverables')}",
        f"min_renders: {get('min_renders')}",
        f"min_render_px: {get('min_render_px')}",
    ]
    for key in ("references", "must_have", "avoid", "acceptance"):
        values = {"references": refs, "must_have": must, "avoid": avoid,
                  "acceptance": accept}[key]
        if values:
            lines.append(f"{key}:")
            lines += [f'  - "{v}"' for v in values]
        else:
            lines.append(f"{key}: []")
    lines += ["---", "", f"# {title}", ""]

    note = (item.get("notes", "") or "").strip()
    if note and note not in (">", "|"):
        lines += [note,
                  "",
                  "> Generated from a pack. Fill in anything the pack left blank before you "
                  "build, and read STANDARDS.md.",
                  ""]
    else:
        lines += ["Generated from a pack. Prose notes were not supplied for this item — if the "
                  "fields above leave a real ambiguity, resolve it in the direction of the "
                  "plainest, most iconic version of the object and record the choice in the "
                  "package README.",
                  ""]

    if parts:
        lines += ["## Parts list", ""]
        lines += [f"{i}. {p}" for i, p in enumerate(parts, 1)]
        lines += [""]
    lines += ["## Out of scope", "", "- animation, rigging, LODs", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Generate briefs from a themed pack file.")
    ap.add_argument("pack", help="path to a .pack file")
    ap.add_argument("--count", type=int, default=1, help="how many briefs to generate")
    ap.add_argument("--list", action="store_true", help="list remaining items, generate nothing")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    pack_path = Path(args.pack)
    if not pack_path.is_absolute():
        pack_path = (Path.cwd() / pack_path).resolve()
    if not pack_path.is_file():
        print(f"error: no such pack: {args.pack}", file=sys.stderr)
        return 2

    pack = parse_pack(pack_path.read_text(encoding="utf-8", errors="replace"))
    name = pack.get("pack") or pack_path.stem
    items = pack.get("items", [])
    if not items:
        print(f"error: {pack_path.name} contains no items (expected an `items:` list)",
              file=sys.stderr)
        return 2

    used = used_slugs()
    remaining = [it for it in items if it.get("slug") and it["slug"] not in used]

    if args.list:
        print(f"pack '{name}': {len(items)} item(s), {len(remaining)} remaining")
        for it in items:
            mark = " " if it.get("slug") in used else "*"
            print(f"  {mark} {it.get('slug', '?'):<34} {it.get('title', '')}")
        print("\n(* = not yet generated)")
        return 0 if remaining else 1

    if not remaining:
        print(f"pack '{name}': nothing left ({len(items)} item(s) already generated)")
        return 1

    count = max(1, args.count)
    number = next_number()
    for item in remaining[:count]:
        missing = [f for f in REQUIRED_ITEM_FIELDS if not item.get(f)]
        if missing:
            print(f"error: pack item is missing {missing}: {item}", file=sys.stderr)
            return 2
        body = build_brief(name, pack, item, number)
        target = BRIEFS / "OPEN" / f"{number:04d}-{item['slug']}.md"
        if args.dry_run:
            print(f"[dry run] would write {target.relative_to(REPO)}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            print(f"wrote {target.relative_to(REPO)}  ({item['title']})")
        number += 1

    if not args.dry_run:
        print(f"\n{min(count, len(remaining))} brief(s) added. Agents claim them with:"
              f"\n  python tools/claim_brief.py --next --agent <slug>")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
