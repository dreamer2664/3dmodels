#!/usr/bin/env python3
"""claim_brief.py — atomic-ish brief queue for the 3dmodels repository.

The repo owner drops briefs into BRIEFS/OPEN/. An agent claims one, builds it, and delivers it.
The claim is recorded with a lock file so two agents starting at the same time cannot take the
same brief.

Usage
-----
    python tools/claim_brief.py --next --agent atlas          # claim the lowest-numbered open brief
    python tools/claim_brief.py --next --agent atlas --dry-run
    python tools/claim_brief.py --status                      # whole queue + stale claims
    python tools/claim_brief.py --show 0007                   # print one brief's front-matter
    python tools/claim_brief.py --release 0007 --agent atlas  # give it back (cannot build it)
    python tools/claim_brief.py --deliver 0007                # after the package is pushed
    python tools/claim_brief.py --new "Brass Lantern" --agent atlas   # agent writes its own brief

What --next does
    1. lists BRIEFS/OPEN/*.md, sorts by the numeric prefix (that is the priority order)
    2. skips any brief that already has a lock file in BRIEFS/CLAIMED/
    3. `git mv`s it into BRIEFS/CLAIMED/ (falls back to shutil.move outside a git repo)
    4. writes BRIEFS/CLAIMED/<brief>.lock.json  {agent, claimed_at, package_path}
    5. creates agent_<slug>/<package>/{model,renders}/ and prints the paths to use

Exit codes
    0 = ok (claimed / delivered / released / listed)
    1 = nothing to do (no open briefs) or invalid state
    2 = usage error or the brief was already claimed by someone else
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRIEFS = REPO / "BRIEFS"
OPEN = BRIEFS / "OPEN"
CLAIMED = BRIEFS / "CLAIMED"
DELIVERED = BRIEFS / "DELIVERED"

STALE_HOURS = 24
BRIEF_RE = re.compile(r"^(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
WORKSPACE_RE = re.compile(r"^agent_[a-z0-9]+(?:_[a-z0-9]+)*$")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dirs() -> None:
    for d in (OPEN, CLAIMED, DELIVERED):
        d.mkdir(parents=True, exist_ok=True)


def git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=check
    )


def git_available() -> bool:
    try:
        return git("rev-parse", "--is-inside-work-tree").returncode == 0
    except Exception:
        return False


def move(src: Path, dst: Path) -> None:
    """git mv when possible (keeps history), plain move otherwise."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if git_available():
        rel_src = src.relative_to(REPO).as_posix()
        rel_dst = dst.relative_to(REPO).as_posix()
        result = git("mv", rel_src, rel_dst)
        if result.returncode == 0:
            return
    shutil.move(str(src), str(dst))


def parse_front_matter(text: str) -> dict[str, str]:
    """Flat `key: value` front-matter parser (handles quoted values, ignores blocks)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t", "-")):
            continue                      # nested list item / continuation
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("#"):
            value = ""
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def lock_path(brief: Path) -> Path:
    return brief.with_suffix(".lock.json")


def read_lock(brief: Path) -> dict | None:
    lp = lock_path(brief)
    if not lp.exists():
        return None
    try:
        return json.loads(lp.read_text(encoding="utf-8"))
    except Exception:
        return {"agent": "?", "claimed_at": "?", "package_path": "?"}


def write_lock(brief: Path, payload: dict) -> Path:
    lp = lock_path(brief)
    lp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return lp


def brief_id(path: Path) -> str:
    m = BRIEF_RE.match(path.name)
    return m.group(1) if m else path.stem


def brief_slug(path: Path) -> str:
    m = BRIEF_RE.match(path.name)
    return m.group(2) if m else path.stem


def open_briefs() -> list[Path]:
    ensure_dirs()
    items = [p for p in OPEN.glob("*.md") if BRIEF_RE.match(p.name)]
    return sorted(items, key=lambda p: p.name)


def claimed_briefs() -> list[Path]:
    ensure_dirs()
    return sorted([p for p in CLAIMED.glob("*.md") if BRIEF_RE.match(p.name)],
                  key=lambda p: p.name)


def find_brief(ident: str) -> Path | None:
    """Find a brief by id (0007) or slug or filename in CLAIMED/ then OPEN/."""
    ident = ident.strip()
    for folder in (CLAIMED, OPEN):
        for p in folder.glob("*.md"):
            if not BRIEF_RE.match(p.name):
                continue
            if ident in (brief_id(p), brief_slug(p), p.name, p.stem):
                return p
    return None


def hours_ago(iso: str) -> float | None:
    try:
        then = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None
    return (datetime.now(timezone.utc) - then).total_seconds() / 3600.0


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_status() -> int:
    ensure_dirs()
    o, c, d = open_briefs(), claimed_briefs(), sorted(DELIVERED.glob("*.md"))

    print(f"\nBRIEF QUEUE  (repo: {REPO})")
    print("=" * 72)

    print(f"\nOPEN ({len(o)}) — ready to be claimed, in this order:")
    if not o:
        print("  (empty — write one from BRIEFS/TEMPLATE.md or generate from a pack)")
    for p in o:
        fm = parse_front_matter(p.read_text(encoding="utf-8", errors="replace"))
        print(f"  {brief_id(p)}  {fm.get('title', brief_slug(p)):<34} "
              f"[{fm.get('category', '?')}]  {fm.get('tri_budget', '')}")

    print(f"\nCLAIMED ({len(c)}):")
    if not c:
        print("  (none)")
    stale = []
    for p in c:
        fm = parse_front_matter(p.read_text(encoding="utf-8", errors="replace"))
        lock = read_lock(p) or {}
        age = hours_ago(lock.get("claimed_at", ""))
        age_s = f"{age:.1f}h ago" if age is not None else "unknown"
        flag = ""
        if age is not None and age > STALE_HOURS:
            flag = "  <-- STALE, consider releasing"
            stale.append(p)
        print(f"  {brief_id(p)}  {fm.get('title', brief_slug(p)):<34} "
              f"agent={lock.get('agent', '?'):<14} {age_s}{flag}")
        if lock.get("package_path"):
            print(f"        package: {lock['package_path']}")

    print(f"\nDELIVERED ({len(d)}):")
    if not d:
        print("  (none)")
    for p in d:
        fm = parse_front_matter(p.read_text(encoding="utf-8", errors="replace"))
        print(f"  {brief_id(p)}  {fm.get('title', brief_slug(p)):<34} "
              f"{fm.get('package_path', '')}")

    print()
    if stale:
        print(f"warning: {len(stale)} claim(s) older than {STALE_HOURS}h. "
              f"Release with: python tools/claim_brief.py --release <id>")
    return 0


def cmd_show(ident: str) -> int:
    p = find_brief(ident)
    if p is None:
        print(f"error: no brief matching '{ident}' in OPEN/ or CLAIMED/", file=sys.stderr)
        return 1
    print(p.read_text(encoding="utf-8"))
    return 0


def cmd_next(agent: str, dry_run: bool, category: str | None) -> int:
    ensure_dirs()
    if not WORKSPACE_RE.match(f"agent_{agent}"):
        print(f"error: --agent must be a slug like 'atlas' (a-z, 0-9, _), got '{agent}'",
              file=sys.stderr)
        return 2

    for p in open_briefs():
        # a brief already moved into CLAIMED cannot be in OPEN, but a stale lock could exist
        if lock_path(p).exists():
            print(f"note: skipping {p.name} — it has a lock file in OPEN/")
            continue
        fm = parse_front_matter(p.read_text(encoding="utf-8", errors="replace"))
        if category and fm.get("category", "").strip() != category:
            continue

        slug = brief_slug(p)
        bid = brief_id(p)
        workspace = f"agent_{agent}"
        package_path = f"{workspace}/{slug}"
        target = CLAIMED / p.name
        payload = {
            "brief_id": bid,
            "slug": slug,
            "title": fm.get("title", slug),
            "agent": workspace,
            "claimed_at": now_iso(),
            "package_path": package_path,
            "status": "claimed",
        }

        if dry_run:
            print(f"[dry run] would claim {p.name} -> CLAIMED/, package {package_path}")
            return 0

        if target.exists():
            print(f"error: {target.name} already exists in CLAIMED/ — claimed by "
                  f"{(read_lock(target) or {}).get('agent', 'someone')}", file=sys.stderr)
            return 2

        try:
            # claim the lock first with O_EXCL semantics: whoever creates it owns the brief
            lock_target = lock_path(target)
            lock_target.parent.mkdir(parents=True, exist_ok=True)
            with open(lock_target, "x", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.write("\n")
        except FileExistsError:
            print(f"note: {p.name} was claimed by another agent a moment ago — "
                  f"trying the next brief")
            continue
        try:
            move(p, target)
        except (FileNotFoundError, OSError) as exc:
            # another process won the race and moved the file; release our lock and move on
            lock_path(target).unlink(missing_ok=True)
            print(f"note: {p.name} disappeared while claiming ({exc.__class__.__name__}) — "
                  f"trying the next brief")
            continue
        lp = lock_path(target)

        pkg_dir = REPO / package_path
        (pkg_dir / "model").mkdir(parents=True, exist_ok=True)
        (pkg_dir / "renders").mkdir(parents=True, exist_ok=True)
        ws_dir = REPO / workspace
        roadmap = ws_dir / "ROADMAP.md"
        if not roadmap.exists():
            tmpl = REPO / "templates" / "02_ROADMAP_TEMPLATE.md"
            if tmpl.exists():
                shutil.copy(tmpl, roadmap)

        print("\nclaimed")
        print(f"  brief        : BRIEFS/CLAIMED/{p.name}")
        print(f"  lock         : {lp.relative_to(REPO)}")
        print(f"  package dir  : {package_path}/  (model/ and renders/ created)")
        if pkg_dir.is_dir() and not (pkg_dir / "README.md").exists():
            tmpl = REPO / "templates" / "01_MODEL_README_TEMPLATE.md"
            if tmpl.exists():
                shutil.copy(tmpl, pkg_dir / "README.md")
                print(f"  readme       : {package_path}/README.md (from template)")
        print(f"\n  Build exactly: {payload['title']}  — {fm.get('category', 'category?')}")
        print(f"  Read the brief: BRIEFS/CLAIMED/{p.name}")
        print("  Next: docs/SETUP.md -> build -> renders -> preflight -> push -> --deliver\n")
        return 0

    msg = "no open briefs left"
    if category:
        msg += f" for category '{category}'"
    print(f"{msg}. Options:\n"
          f"  - ask the owner for more briefs\n"
          f"  - generate one from a pack: python tools/brief_from_pack.py packs/<name>.pack --count 1\n"
          f"  - write your own: python tools/claim_brief.py --new \"<Asset Title>\" --agent {agent}")
    return 1


def cmd_release(ident: str, agent: str | None, note: str) -> int:
    p = find_brief(ident)
    if p is None or p.parent != CLAIMED:
        print(f"error: '{ident}' is not a claimed brief", file=sys.stderr)
        return 1
    lock = read_lock(p) or {}
    if agent and lock.get("agent") and lock["agent"] != f"agent_{agent}":
        print(f"error: {p.name} is claimed by {lock['agent']}, not agent_{agent}", file=sys.stderr)
        return 2
    target = OPEN / p.name
    move(p, target)
    lp = lock_path(p)
    if lp.exists():
        lp.unlink()
    if note:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"\n---\n\n## Released by {lock.get('agent', 'an agent')} "
                     f"on {now_iso()}\n\n{note}\n")
    print(f"released {p.name} back to BRIEFS/OPEN/")
    return 0


def cmd_deliver(ident: str, agent: str | None) -> int:
    p = find_brief(ident)
    if p is None or p.parent != CLAIMED:
        print(f"error: '{ident}' is not a claimed brief", file=sys.stderr)
        return 1
    lock = read_lock(p) or {}
    if agent and lock.get("agent") and lock["agent"] != f"agent_{agent}":
        print(f"error: {p.name} is claimed by {lock['agent']}, not agent_{agent}", file=sys.stderr)
        return 2

    package_path = lock.get("package_path", "")
    pkg = REPO / package_path if package_path else None
    renders = 0
    if pkg and (pkg / "renders").is_dir():
        renders = len(list((pkg / "renders").glob("*.png")))
    problems = []
    if pkg:
        if not (pkg / "README.md").exists():
            problems.append("README.md missing")
        if not list((pkg / "model").glob("*.glb")):
            problems.append("no .glb in model/")
        if not list((pkg / "model").glob("*.blend")):
            problems.append("no .blend in model/")
        if not (pkg / "renders.zip").exists():
            problems.append("renders.zip missing")
        if renders < 5:
            problems.append(f"only {renders} render(s)")
    if problems:
        print(f"warning: delivering an incomplete package ({', '.join(problems)}). "
              f"Run: python tools/preflight.py {package_path}", file=sys.stderr)

    lock.update({
        "status": "delivered",
        "delivered_at": now_iso(),
        "renders": renders,
    })
    write_lock(p, lock)
    target = DELIVERED / p.name
    move(p, target)
    lp = lock_path(p)
    if lp.exists():
        move(lp, DELIVERED / lp.name)

    print(f"delivered {p.name} -> BRIEFS/DELIVERED/")
    if package_path:
        print(f"  package : {package_path}  ({renders} render(s))")
    print("  remember to commit the move together with your package:\n"
          f"    git add {package_path or 'agent_<slug>'} BRIEFS && "
          f"git commit -m \"feat({brief_slug(p)}): deliver brief {brief_id(p)}\"")
    return 0


def cmd_new(title: str, agent: str, category: str, dry_run: bool) -> int:
    """Create a brief (agent-authored, when the queue is empty or for a prompt-specified asset)."""
    ensure_dirs()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        print("error: title produces an empty slug", file=sys.stderr)
        return 2
    numbers = [int(brief_id(p)) for p in list(OPEN.glob("*.md")) + list(CLAIMED.glob("*.md"))
               if BRIEF_RE.match(p.name)]
    next_num = (max(numbers) + 1) if numbers else 1
    filename = f"{next_num:04d}-{slug}.md"
    target = OPEN / filename
    tmpl = BRIEFS / "TEMPLATE.md"
    body = tmpl.read_text(encoding="utf-8") if tmpl.exists() else "---\n---\n"
    body = body.replace('id: "0000"', f'id: "{next_num:04d}"')
    body = body.replace("slug: kebab-case-asset-name", f"slug: {slug}")
    body = body.replace("title: Human Readable Asset Name", f"title: {title}")
    body = body.replace("category: hard-surface-prop", f"category: {category}")
    body = body.replace("origin: owner", f"origin: agent   # written by agent_{agent}")
    if dry_run:
        print(f"[dry run] would write BRIEFS/OPEN/{filename}")
        return 0
    target.write_text(body, encoding="utf-8")
    print(f"created BRIEFS/OPEN/{filename}")
    print("  fill in dimensions_m, must_have, avoid and the parts list before you build —")
    print("  a vague brief produces a vague model. Then claim it with --next.")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Claim / release / deliver briefs for the 3dmodels repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See BRIEFS.md for the full workflow.",
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--next", action="store_true", help="claim the lowest-numbered open brief")
    g.add_argument("--status", action="store_true", help="show the queue")
    g.add_argument("--show", metavar="ID", help="print one brief (id, slug or filename)")
    g.add_argument("--release", metavar="ID", help="return a claimed brief to OPEN/")
    g.add_argument("--deliver", metavar="ID", help="move a finished brief to DELIVERED/")
    g.add_argument("--new", metavar="TITLE", help="create a new brief (agent-authored)")

    ap.add_argument("--agent", help="your slug without the agent_ prefix, e.g. atlas")
    ap.add_argument("--category", help="only claim a brief of this category (with --next)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note", default="", help="reason, recorded when releasing")
    args = ap.parse_args(argv)

    if args.status:
        return cmd_status()
    if args.show:
        return cmd_show(args.show)
    if args.release:
        if not args.agent:
            print("error: --release needs --agent <slug> (or pass it to identify the claim)",
                  file=sys.stderr)
        return cmd_release(args.release, args.agent, args.note)
    if args.deliver:
        return cmd_deliver(args.deliver, args.agent)
    if args.new:
        if not args.agent:
            print("error: --new needs --agent <slug>", file=sys.stderr)
            return 2
        return cmd_new(args.new, args.agent, args.category or "hard-surface-prop", args.dry_run)
    if args.next:
        if not args.agent:
            print("error: --next needs --agent <slug> so the claim can be attributed",
                  file=sys.stderr)
            return 2
        return cmd_next(args.agent, args.dry_run, args.category)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
