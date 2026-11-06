# BRIEFS.md — telling agents what to build

The repo deliberately does **not** let agents choose their own subject any more. You say what to
build; the repo makes that instruction unambiguous, atomic (two agents can't take the same job), and
verifiable.

---

## 1. The one-screen version

```bash
# 1. write a brief (copy the template, fill the blanks) — this is the only creative decision you make
cp BRIEFS/TEMPLATE.md BRIEFS/OPEN/0007-brass-portable-lantern.md
#    edit: slug, asset, dimensions, category, style, must-haves, avoid, references, tri budget

# 2. commit it
git add BRIEFS/OPEN && git commit -m "brief(0007): brass portable lantern" && git push

# 3. tell the agent just this:
#    "Work the next open brief in 3dmodels: docs/SETUP.md, then BRIEFS.md §4, then build it."
```

That's it. The agent runs `tools/claim_brief.py --next`, which moves the brief to `CLAIMED/`,
creates `agent_<slug>/<package>/` from it, and writes `BRIEF.lock.json` so a second agent cannot take
the same one. When it's finished, `tools/claim_brief.py --deliver` moves the brief to `DELIVERED/`.

---

## 2. Folder layout

```
BRIEFS/
├── TEMPLATE.md          ← copy this for every new brief
├── OPEN/                ← you write here. Agents may read, never write.
├── CLAIMED/             ← moved here by `claim_brief.py --next`; agent owns it until delivery
└── DELIVERED/           ← moved here by `claim_brief.py --deliver`; your audit trail
```

| Actor | OPEN | CLAIMED | DELIVERED |
| --- | --- | --- | --- |
| You (owner) | create, edit, delete, reorder (the number prefix is the order) | may reclaim or edit | archive |
| Agent | read only | may update `status` inside its own brief | write via `--deliver` only |

File naming: **`NNNN-kebab-slug.md`**, zero-padded, four digits. The number *is* the priority —
`--next` always picks the lowest number in `OPEN/`. To jump the queue, give the brief a lower number
(e.g. `0001-…`).

---

## 3. Writing a brief

Every field matters. This is where your standards turn into a concrete job:

```yaml
---
id: "0007"
slug: brass-portable-lantern        # becomes folder + package + file names
title: Brass Portable Lantern
category: hard-surface-prop
priority: normal                    # low | normal | high (informational; the number decides order)
style: stylised-realistic           # see STANDARDS.md §1
dimensions_m: {x: 0.162, y: 0.162, z: 0.312}   # or "approx 30 cm tall"
tri_budget: 20000-80000
deliverables: [glb, blend, renders, zip, readme]   # never change this
min_renders: 5
min_render_px: 1600
references:                         # descriptions + links; no images committed without a licence
  - "late-19th-c railway hand lanterns: flared spun-brass base, domed vent, wire bail"
  - "https://example.org/museum/lantern-1879 (photo reference only, do not redistribute)"
must_have:
  - hinged side door with a visible hinge pin
  - four glass guard wires
  - wick adjuster knob with knurling
avoid:
  - soot or heavy damage
  - legible branding or maker's marks
acceptance:                         # extra checks beyond STANDARDS.md; preflight enforces the rest
  - glass reads as glass in the hero shot
  - bail handle is a separate object so it can be posed
---

# Notes (prose, for the agent)

Anything not covered by the fields: intent, context, what it's for, what "good" looks like. Keep it
factual; leave adjectives out.
```

**Rules that make briefs work**

- **Be specific or don't write it.** "A sword" produces four different swords from four agents.
  "Late-medieval arming sword, 0.95 m blade, disc pommel, leather-wrapped grip, scabbard included" produces
  what you wanted.
- **Give real dimensions.** They are the single strongest anti-drift instruction: they force the
  agent's proportions and make the result comparable across models.
- **`avoid` is as important as `must_have`.** It is where you stop the agent's default taste.
- **References are for looking, not for committing.** Links + descriptions. No third-party images in
  the repo without a licence line.
- **Don't restate the technical standards.** Do not write "must be manifold, PBR, 1600px renders" —
  that is `STANDARDS.md` and it already applies. The brief is *subject matter*, not craft.
- If you can't be bothered to write a brief: use a **PACK** (below).

---

## 4. What the agent does with it

Add this to the prompt you send (`AGENT_PROMPT.md` has the full version):

```
Assignment: run `python tools/claim_brief.py --next --agent <your-slug>` from the repo root.
That command assigns you the lowest-numbered open brief, creates your package folder and
writes a lock file. Build exactly the asset described in BRIEFS/CLAIMED/<brief>.md.
Do not substitute your own idea. If the brief is genuinely unbuildable, report why and
release it with `python tools/claim_brief.py --release <brief-id>`.
When the package passes preflight and is pushed, run
`python tools/claim_brief.py --deliver <brief-id>` and commit the move.
```

Agent flow:

```bash
cd 3dmodels
bash tools/setup_blender.sh && source ~/.local/blender/activate.sh
python tools/claim_brief.py --next --agent atlas      # -> CLAIMED/0007-…, creates agent_atlas/brass-portable-lantern/
# ... build, render, look at renders, README, preflight ...
python tools/preflight.py agent_atlas                 # must exit 0
git add agent_atlas BRIEFS && git commit -m "feat(brass-portable-lantern): add model (brief 0007)"
git push                                              # branch + PR as usual
python tools/claim_brief.py --deliver 0007            # moves the brief to DELIVERED/
```

### Claim semantics (why two agents can't collide)

- `--next` takes the lowest-numbered file in `OPEN/`, `git mv`s it into `CLAIMED/`, and writes
  `CLAIMED/<brief>.lock.json` containing the agent slug, UTC timestamp and package path.
- If a lock already exists, `--next` **skips** it and takes the next brief — so parallel agents can
  be started simultaneously without coordination.
- `--release <id>` puts a claimed brief back in `OPEN/` and deletes the lock (use it when you
  genuinely cannot build the asset, with a note in your PR).
- `--deliver <id>` moves brief + lock to `DELIVERED/` and records the package path and render count.
- `--status` prints the queue, including stale claims (claimed more than 24 h ago with no commit).
- Everything is plain `git mv` + JSON, so conflicts surface as normal git conflicts, not silent
  double-work.

---

## 5. Packs — when you don't want to write briefs

A **pack** is one file that generates the next brief itself, in order. Use it to kickstart a themed
batch without writing 40 briefs by hand.

```bash
python tools/brief_from_pack.py packs/kitchen-tools.pack --count 1   # writes the next OPEN brief
python tools/brief_from_pack.py packs/kitchen-tools.pack --list      # show remaining items
```

A pack is a YAML list of subjects with the fields a brief needs:

```yaml
pack: kitchen-tools
category: hard-surface-prop
style: stylised-realistic
defaults:
  tri_budget: 15000-60000
  min_renders: 5
  min_render_px: 1600
items:
  - slug: cast-iron-skillet
    title: Cast Iron Skillet
    dimensions_m: {x: 0.32, y: 0.26, z: 0.05}
    must_have: [pour spouts on both sides, helper handle, seasoning patina, maker's mark ground off]
    avoid: [food residue, chipped enamel]
  - slug: brass-mortar-and-pestle
    ...
```

The generated brief is a normal brief — the agent never knows the difference. Two packs are included
as starting points: `packs/basic-props.pack` and `packs/hand-tools.pack`.

---

## 6. When you don't even want to pick the subject

If you just say "make something good", the agent falls back to the documented default:
read `BRIEFS/OPEN/`, and if it is empty, create its own brief from
`BRIEFS/TEMPLATE.md` **inside its own workspace** at `agent_<slug>/_briefs/` and build from that. It is
still required to obey `STANDARDS.md`, and the brief it wrote becomes part of the audit trail. This is
the least-preferred path — your subject choices are better than the agent's.

You can also say it directly in the prompt, without any file:

> Build a single **cast-iron woodworking plane, 45 cm long, No. 7 style, rosewood handles**. Everyone
> else in the swarm is on the brief queue; you are the exception. Follow the repo standards exactly.

Agents are told to treat an explicit asset in their prompt as **brief #0** — highest priority,
overriding the queue — and record it in their package README's front-matter as
`brief_source: prompt`.

---

## 7. Ordering, dedup and quotas you control

| You want | Do this |
| --- | --- |
| One agent, one specific asset | put it in the prompt (`brief #0`), no queue involvement |
| Many agents, no duplicates | put 1 brief per agent in `OPEN/` and send them all the same instruction |
| A themed batch of 20 | write a `.pack`, then run `--next` per agent |
| Priority jump | renumber a brief (`git mv BRIEFS/OPEN/0021-x.md BRIEFS/OPEN/0003-x.md`) |
| Hold an idea without assigning it | keep it in `OPEN/` — `--next` will hand it out, so if it must wait, park it in `BRIEFS/DELIVERED/` or a `PARKED/` folder you create |
| Re-do an asset | write a `fix(<package>)` note in a new brief referencing the delivered one, or edit the delivered brief's `status` |

---

## 8. Checking what came back

`BRIEFS/DELIVERED/` + `git log` is your audit trail. Each delivered brief records `package_path`,
`renders` and `delivered_at`, so you can verify the agent built the thing you asked for, not a
neighbouring thing:

```bash
python tools/claim_brief.py --status          # OPEN / CLAIMED / DELIVERED with package paths
git log --oneline -- BRIEFS/                  # the paper trail
```

The judgement call — is it *good* — is still yours; the repo's job is to make sure the asset you get
is the asset you specified, finished, and documented.
