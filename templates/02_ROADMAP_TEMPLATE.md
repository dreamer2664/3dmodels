# ROADMAP — `agent_<your-slug>`

> Copy this file to `agent_<slug>/ROADMAP.md` and fill it in **before** you start modelling.
> Keeping it current lets a human see what you're doing without interrupting you.

**Agent slug:** `agent_<slug>`
**Started:** <YYYY-MM-DD>
**Primary category:** <hard-surface-prop / architecture / organic / vehicle / environment / stylised / product-viz>
**Toolchain:** <Blender 4.2 headless, Cycles / other>

---

## Finish line (this run, not later)

- [ ] Blender installed (`tools/setup_blender.sh`)
- [ ] Model, materials, renders, wireframe + scale pass done
- [ ] Every render opened and inspected, ≥ 2 iterations
- [ ] `.glb` + `.blend` exported and re-verified
- [ ] README complete, limitations honest, `status: released`
- [ ] `renders.zip` rebuilt after the last render
- [ ] `python tools/preflight.py agent_<slug>` exits 0
- [ ] Branch pushed, PR open with preflight + framing output

I will not end my run until every box above is ticked. (docs/NO_STOPPING.md)

---

## Current package

| Field | Value |
| --- | --- |
| Wanted line | `<the line you took from WANTED.md>` (or `prompt-specified`) |
| Package | `<kebab-case-asset-name>` |
| What it is | <one precise sentence — not "a robot", but "shoulder-mounted industrial welding arm, hydraulic, 1.4 m reach"> |
| Category | <category> |
| Target tri count | <00000> |
| Target dimensions | <0.00 × 0.00 × 0.00> m |
| Status | `planned` / `blockout` / `modelling` / `materials` / `rendering` / `docs` / `released` |

### References I will consult (not commit)

- <e.g. museum photographs of 19th-century railway lanterns — described in NOTES.md>
- <e.g. standard 3/8" BSP thread dimensions>
- <e.g. human-scale comparison: standard door 2.05 m>

### Design decisions

- <e.g. Realistic PBR finish, mild wear but no heavy damage so the asset stays reusable.>
- <e.g. Single material set to keep engine integration simple.>

### Risks / unknowns

- <e.g. Glass transmission may look flat in EEVEE; will test both renderers.>

---

## Backlog (next packages)

| # | Package | What it is | Category | Priority |
| --- | --- | --- | --- | --- |
| 1 | `<kebab-name>` | <one precise sentence> | <category> | high |
| 2 | `<kebab-name>` | <one precise sentence> | <category> | medium |
| 3 | `<kebab-name>` | <one precise sentence> | <category> | low |

Backlog entries must stay specific. "More props" is not an entry.

---

## Completed packages

| Package | Released | Tris | Renders | Notes |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

---

## Log

- <YYYY-MM-DD> — workspace created; first package scoped.
- <YYYY-MM-DD> — <milestone>
