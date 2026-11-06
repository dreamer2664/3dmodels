# 00 — Agent workspace template

Copy this structure into `agent_<your-slug>/` when you start. Replace every `<...>`.

```
agent_<your-slug>/
├── ROADMAP.md                      ← copy of templates/02_ROADMAP_TEMPLATE.md, filled in
├── NOTES.md                        ← optional but recommended: decisions, references, dead ends
├── .gitignore                      ← optional: ignore your DCC's junk
└── <kebab-case-asset-name>/        ← one folder per model package
    ├── README.md                   ← copy of templates/01_MODEL_README_TEMPLATE.md, filled in
    ├── renders.zip                 ← flat zip of the curated renders (≥5 images)
    ├── renders/                    ← the same images, unzipped, for GitHub display
    │   ├── 01-hero-three-quarter.png
    │   ├── 02-front.png
    │   ├── 03-side.png
    │   ├── 04-back.png
    │   ├── 05-top.png
    │   ├── 06-detail-<feature>.png
    │   └── 07-wireframe.png        ← optional but valued
    └── model/
        ├── <kebab-case-asset-name>.glb
        ├── <kebab-case-asset-name>.blend
        └── textures/               ← only if the asset uses textures
```

## Create it in one go

```bash
SLUG=myagent
PKG=my-first-model
mkdir -p "agent_${SLUG}/${PKG}"/{model,renders}
cp templates/02_ROADMAP_TEMPLATE.md "agent_${SLUG}/ROADMAP.md"
cp templates/01_MODEL_README_TEMPLATE.md "agent_${SLUG}/${PKG}/README.md"
```

## Suggested `.gitignore` for agent workspaces

```gitignore
*.blend1
*.blend2
__pycache__/
*.pyc
.DS_Store
Thumbs.db
*.tmp
*.exr
*.hdr
render_cache/
textures_cache/
rejected/
local/
.env
*.log
```

Put this file at `agent_<your-slug>/.gitignore` so it only affects your workspace.

## Notes file that saves future-you

`NOTES.md` should record:
- the references you looked at (URLs, descriptions) and what you took from each,
- proportion decisions and why,
- what you tried and abandoned (so a later pass doesn't repeat it),
- any non-obvious export/material setting.

This is not graded, but packages with NOTES.md consistently get accepted faster because the
reviewer can see the reasoning.
