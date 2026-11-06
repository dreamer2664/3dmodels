# PR template
#
# Opened with this file automatically. Fill every field — an empty field is a
# reason to have the PR bounced.

## Package

- **Workspace:** `agent_<slug>`
- **Package path:** `agent_<slug>/<package>`
- **Asset:** <what it is, one sentence>
- **Category:** `<hard-surface-prop | architecture | organic | vehicle | environment | stylised | product-viz>`
- **Triangle count:** <00000>
- **Renders:** <0> images at <1600>×<1600>, archived in `renders.zip`
- **Toolchain:** <Blender 4.2 / Cycles / other>

## Preflight

```
<paste the output of: python tools/preflight.py agent_<slug>>
```

## Definition of done

- [ ] Layout matches `AGENTS.md` §1 (mesh, source, renders, zip, README all present)
- [ ] Every render opened and visually inspected by me (and the contact sheet)
- [ ] Full model in frame in every shot, no clipping, ≥ 5 views
- [ ] Real-world metric scale, origin at ground centre, transforms applied
- [ ] `.glb` re-imported and verified against the renders
- [ ] README complete, no placeholders, limitations stated honestly
- [ ] `tools/preflight.py` exits 0
- [ ] Nothing outside my workspace modified

## Honest gaps

<Anything you could not meet from STANDARDS.md, and why. Write "none" only if genuinely none.>

## Notes for the reviewer

<Design decisions, anything unusual about the asset, what you'd do with more time.>
