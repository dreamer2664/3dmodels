---
# BRIEF TEMPLATE — copy to BRIEFS/OPEN/NNNN-kebab-slug.md and fill every field.
# The NNNN number is the queue order: --next always takes the lowest number in OPEN/.
id: "0000"
slug: kebab-case-asset-name
title: Human Readable Asset Name
category: hard-surface-prop   # hard-surface-prop | architecture | organic | vehicle | environment | stylised | product-viz
priority: normal              # low | normal | high  (informational — the number decides order)
status: open                  # open | claimed | delivered   (agents flip this to claimed, then delivered)
style: stylised-realistic     # stylised-realistic | photoreal | stylised | low-poly
origin: owner                 # owner | agent | prompt  (who asked for this asset)
dimensions_m: {x: 0.000, y: 0.000, z: 0.000}   # or: "approx 30 cm tall" — real-world metres
tri_budget: 20000-80000
deliverables: [glb, blend, renders, zip, readme]   # do not change
min_renders: 5
min_render_px: 1600
references:
  - "what to look at for form and proportion (description)"
  - "optional link (reference only — do not redistribute the image)"
must_have:
  - a feature that must be present and visible in the renders
  - another one
avoid:
  - something this asset must not have
  - a cliché to steer away from
acceptance:
  - an extra check beyond STANDARDS.md, stated so a reviewer can say yes/no
---

# Notes

Prose for the agent: intent, context, what the asset is for, what good looks like. Keep it factual
and specific. Do not restate technical standards (manifold geometry, PBR, render sizes) — those live
in `STANDARDS.md` and apply automatically.

## Parts list (optional but strongly recommended)

Enumerating the components is the cheapest way to get a complete model instead of a suggestive blob:

1. main body — <material, finish>
2. <sub-part> — <material, function>
3. ...

## Out of scope

- animation, rigging, LODs (unless stated above)
- <anything else the agent should not spend time on>
