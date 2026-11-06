#!/usr/bin/env python3
"""wanted.py — let the owner list models in plain lines; let agents take one.

WANTED.md is a simple checklist. Agents never edit the list themselves; they use this tool.

Owner (in WANTED.md):
    ## To build
    - [ ] brass portable lantern, about 30 cm tall, glass globe
    - [ ] cast iron skillet

Agent:
    python tools/wanted.py --next --agent atlas     # take the top unclaimed line
    python tools/wanted.py --release 1              # put it back (with --note "why")
    python tools/wanted.py --done 1                 # mark it finished once pushed
    python tools/wanted.py --list                   # see the list from the terminal

Exit codes: 0 ok, 1 nothing to do, 2 usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:            # Windows
    fcntl = None

REPO = Path(__file__).resolve().parent.parent
WANTED = REPO / "WANTED.md"

OPEN_BOXES = ("- [ ]", "- [x]", "- [X]", "- [~]")
ITEM_RE = re.compile(r"^- \[( |x|X|~)\]\s+(.*)$")
CLAIM_RE = re.compile(r"\s*\(taken by (agent_[a-z0-9_]+)[^)]*\)\s*$")


FILLER = {
    "a", "an", "the", "some", "one", "two", "three", "pair", "of", "new", "simple",
    "small", "large", "big", "please", "make", "build", "create", "model", "3d",
}


def slugify(text: str) -> str:
    """'a small brass lantern, 30cm' -> 'brass-lantern' (good enough to build on)."""
    text = CLAIM_RE.sub("", text)
    head = re.split(r"[,;(]", text)[0]
    head = re.split(r"\s(?:about|approx|around|roughly|~)\s", head)[0]
    head = re.split(r"\s(?:with|and|plus|including|that|which)\s", head)[0]
    words = [w for w in re.findall(r"[a-z0-9]+", head.lower())]
    # strip filler from the front ("build me a wooden…" -> "wooden…")
    while words and words[0] in FILLER | {"me", "us", "my", "our", "i", "want", "need"}:
        words.pop(0)
    while len(words) > 3 and words[0] in FILLER:
        words.pop(0)
    while len(words) > 4:
        words.pop()
    slug = "-".join(words).strip("-")
    return slug or "model"


@contextlib.contextmanager
def locked():
    """Serialise read-modify-write of WANTED.md so two agents can't take the same line."""
    lock_file = WANTED.with_suffix(".md.lock")
    if fcntl is None:
        # crude exclusive-create spin, good enough for the fallback
        for _ in range(600):
            try:
                fd = lock_file.open("x")
                break
            except FileExistsError:
                time.sleep(0.05)
        else:
            raise SystemExit("error: could not lock WANTED.md (stale .lock file?)")
        try:
            yield
        finally:
            fd.close()
            lock_file.unlink(missing_ok=True)
        return
    with open(lock_file, "w", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def load() -> list[str]:
    stale = WANTED.with_suffix(".md.lock")
    if fcntl is None and stale.exists():
        try:
            if time.time() - stale.stat().st_mtime > 120:
                stale.unlink()
        except OSError:
            pass
    if not WANTED.exists():
        raise SystemExit(f"error: {WANTED} not found — run this from the repo root")
    return WANTED.read_text(encoding="utf-8").splitlines()


def save(lines: list[str]) -> None:
    """Write back, removing runs of blank lines and stray blanks right after headings."""
    out: list[str] = []
    for line in lines:
        if not line.strip() and out and (not out[-1].strip() or len(out) == 1):
            continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    WANTED.write_text("\n".join(out) + "\n", encoding="utf-8")


def section_bounds(lines: list[str]) -> tuple[int, int, int]:
    """Return (to_build_start, to_build_end, done_start) line indexes."""
    to_start = next((i for i, l in enumerate(lines) if l.strip().lower() == "## to build"), None)
    if to_start is None:
        raise SystemExit("error: WANTED.md needs a '## To build' heading")
    done = next(
        (i for i, l in enumerate(lines) if i > to_start and l.strip().lower().startswith("## done")),
        len(lines),
    )
    return to_start, done, done


def items(lines: list[str]) -> list[tuple[int, str, str, str]]:
    """(line_index, state, text, slug) for every checklist line under ## To build."""
    to_start, to_end, _ = section_bounds(lines)
    out = []
    for i in range(to_start, to_end):
        m = ITEM_RE.match(lines[i])
        if m:
            state = "done" if m.group(1) in "xX" else ("claimed" if m.group(1) == "~" else "open")
            out.append((i, state, m.group(2).strip(), slugify(m.group(2))))
    return out


def cmd_list() -> int:
    lines = load()
    rows = items(lines)
    if not rows:
        print("WANTED.md has nothing to build — add lines under '## To build'")
        return 1
    print(f"\nWANTED ({len(rows)} item(s)):")
    for n, (_, state, text, slug) in enumerate(rows, 1):
        mark = {"open": "  ", "claimed": "->", "done": "ok"}[state]
        print(f"  {n:>2}. {mark} {text}")
        print(f"         package slug: {slug}/")
    print("\nAgents: python tools/wanted.py --next --agent <slug>\n")
    return 0


def cmd_next(agent: str, dry_run: bool) -> int:
    if dry_run:
        return _cmd_next(agent, True)
    with locked():
        return _cmd_next(agent, False)


def _cmd_next(agent: str, dry_run: bool) -> int:
    lines = load()
    rows = items(lines)
    if not rows:
        print("nothing on the wanted list. Tell the owner, or pick a subject yourself and "
              "follow STANDARDS.md.")
        return 1
    for index, state, text, slug in rows:
        if state != "open":
            continue
        workspace = f"agent_{agent}"
        package_path = f"{workspace}/{slug}"
        if dry_run:
            print(f"[dry run] would take: {text}\n          package: {package_path}/")
            return 0
        lines[index] = f"- [~] {text} (taken by {workspace})"
        save(lines)
        pkg = REPO / package_path
        (pkg / "model").mkdir(parents=True, exist_ok=True)
        (pkg / "renders").mkdir(parents=True, exist_ok=True)
        readme = pkg / "README.md"
        if not readme.exists():
            tmpl = REPO / "templates" / "01_MODEL_README_TEMPLATE.md"
            if tmpl.exists():
                body = tmpl.read_text(encoding="utf-8")
                body = body.replace("<package-name>", slug).replace("<agent_slug>", workspace)
                readme.write_text(body, encoding="utf-8")
        print(f"you are building: {text}")
        print(f"  package : {package_path}/   (model/ and renders/ ready)")
        print(f"  slug    : {slug}")
        print(f"  line    : now marked [~] taken by {workspace} in WANTED.md")
        print("\nnext: docs/SETUP.md -> build -> renders -> preflight -> push -> "
              f"python tools/wanted.py --done <number>")
        return 0
    print("everything on the list is already taken or done. "
          "Ask the owner for more, or pick a subject yourself.")
    return 1


def _find(lines: list[str], number: int) -> tuple[int, str, str, str] | None:
    rows = items(lines)
    if not 1 <= number <= len(rows):
        return None
    return rows[number - 1]


def cmd_release(number: int, note: str) -> int:
    with locked():
        return _cmd_release(number, note)


def _cmd_release(number: int, note: str) -> int:
    lines = load()
    row = _find(lines, number)
    if row is None:
        print(f"error: no item #{number} in the list", file=sys.stderr)
        return 2
    index, state, text, _ = row
    if state != "claimed":
        hint = "already finished" if state == "done" else "not taken by anyone"
        print(f"error: item #{number} ({text}) is {hint}", file=sys.stderr)
        return 1
    text = CLAIM_RE.sub("", text)
    lines[index] = f"- [ ] {text}"
    save(lines)
    print(f"released #{number}: {text}")
    if note:
        print(f"  note for the owner (put this in your PR): {note}")
    return 0


def cmd_done(number: int, package: str | None) -> int:
    with locked():
        return _cmd_done(number, package)


def _cmd_done(number: int, package: str | None) -> int:
    lines = load()
    row = _find(lines, number)
    if row is None:
        print(f"error: no item #{number} in the list", file=sys.stderr)
        return 2
    index, _, text, slug = row
    text = CLAIM_RE.sub("", text)
    where = package or slug
    _, _, done_start = section_bounds(lines)
    lines[index] = None          # remove the line from To build
    lines = [ln for ln in lines if ln is not None]
    # re-find the Done heading after the removal and insert beneath it
    done_heading = next(
        (i for i, l in enumerate(lines) if l.strip().lower().startswith("## done")),
        len(lines),
    )
    insert_at = done_heading + 1
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1
    lines.insert(insert_at, f"- [x] {text} — `{where}`")
    save(lines)
    print(f"done #{number}: {text}")
    print(f"  moved under '## Done' with folder {where}")
    print("  commit WANTED.md together with your package")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Work the owner's WANTED.md list.",
        epilog="The owner just writes lines. Agents use --next / --done.",
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--next", action="store_true", help="take the top unclaimed item")
    g.add_argument("--list", action="store_true", help="show the list")
    g.add_argument("--done", type=int, metavar="N", help="mark item N finished")
    g.add_argument("--release", type=int, metavar="N", help="give item N back")
    ap.add_argument("--agent", help="your slug, e.g. atlas (required for --next)")
    ap.add_argument("--package", help="folder to record with --done (defaults to the slug)")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        return cmd_list()
    if args.next:
        if not args.agent:
            print("error: --next needs --agent <slug>", file=sys.stderr)
            return 2
        return cmd_next(args.agent, args.dry_run)
    if args.done is not None:
        return cmd_done(args.done, args.package)
    if args.release is not None:
        return cmd_release(args.release, args.note)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
