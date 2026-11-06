# SETUP.md — install the toolchain, then work

**Read this before you report that something is missing.**

Sandboxes do not ship Blender. That is expected. It is **your job to install it**, not a reason to
stop. Every package list and command you need is below, and [`tools/setup_blender.sh`](../tools/setup_blender.sh)
does the whole install automatically in about 20 seconds.

> ### The rule
> "There is no Blender in this sandbox" is **not an acceptable statement**.
> "I could not install Blender because &lt;exact error&gt; after trying &lt;these steps&gt;" is.
> Before you are allowed to write the second sentence you must have run
> `bash tools/setup_blender.sh` and pasted its final output.

---

## 1. One command (recommended)

```bash
git clone https://github.com/dreamer2664/3dmodels.git
cd 3dmodels
bash tools/setup_blender.sh          # ~20 s: downloads Blender 4.2 LTS, fixes missing libs
source ~/.local/blender/activate.sh  # adds blender to PATH + LD_LIBRARY_PATH
blender --version                    # must print: Blender 4.2.23 LTS
```

The script:
1. skips the install if a working `blender` is already on `PATH`;
2. downloads the official Linux tarball (three mirrors, retries) into `~/.cache/3dmodels`;
3. extracts to `~/.local/blender` — **no root required**;
4. runs `ldd`, finds missing shared libraries, `apt-get download`s the `.deb`s that provide them
   and unpacks them locally (this is what fixes the classic `libxkbcommon.so.0: cannot open shared
   object file` failure without sudo);
5. writes `~/.local/blender/activate.sh` and verifies `blender --version` actually runs;
6. checks `numpy` / `Pillow` for the repo tools.

Options: `BLENDER_VERSION=4.5.3`, `BLENDER_CHANNEL=Blender4.5`, `BLENDER_PREFIX=/somewhere` as env vars.

---

## 2. What you need, and why

| Requirement | Needed for | If missing |
| --- | --- | --- |
| **Blender ≥ 3.6** (4.2 LTS recommended) | authoring, `.blend` source, Cycles renders, `.glb` export | install it (§1). There is no compliant substitute for the `.blend` deliverable |
| `git` | clone / branch / push | install it; it is present in virtually every sandbox |
| `python3` ≥ 3.8 | `tools/preflight.py`, `check_glb.py`, `make_render_sheet.py` | install it (`apt-get install python3` or the distro equivalent) |
| `curl` **or** `wget` | downloading Blender, CC0 HDRIs | one of them is always present |
| `unzip` / `zip` | `renders.zip` | if absent, build the zip with Python (`CONTRIBUTING.md` §1 has the snippet) |
| **CPU + ~2 GB free disk** | headless Cycles rendering | reduce render resolution/samples; Blender unpacks to ~1.5 GB |
| *(optional)* `numpy`, `Pillow` | extra image checks, contact sheets | the tools skip those checks gracefully; Blender has its own numpy |
| *(optional)* `xvfb` | only if you insist on EEVEE headless | **don't** — use Cycles CPU, EEVEE needs a GPU surface and fails in sandboxes |
| **≥ 3 GB RAM** for the default path | OpenImageDenoise at ≥ 1400 px needs ~1–1.5 GB and is **OOM-killed** below that | the rig detects this and switches to `--no-denoise` + built-in post-denoise automatically; nothing to install |

### Python packages, explicitly

Nothing outside the standard library is required for validation:

```bash
python3 -m pip install --quiet numpy pillow        # optional, improves checks
# on distros with PEP 668 protection:
python3 -m pip install --quiet --break-system-packages numpy pillow
```

Blender's bundled Python already contains `numpy`; `tools/render_rig.py` reads it from there, so the
render pipeline works with **zero** pip installs.

### System packages (only if you are root and want the apt route)

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  libxkbcommon0 libgl1 libxi6 libxrender1 libxext6 libxfixes3 libxxf86vm1 \
  libsm6 libice6 libxinerama1 libxrandr2 libxcursor1 libgomp1
```

Without sudo, `tools/setup_blender.sh` reproduces exactly this set from `.deb` files into a private
directory. That is the supported path in sandboxes.

---

## 3. Renderer choice in a sandbox

| Attempt | Result | Use it? |
| --- | --- | --- |
| `Cycles`, `device = CPU` | works everywhere, deterministic | **yes — default** |
| `Cycles`, `device = GPU` (OptiX/CUDA) | needs a GPU + drivers; usually absent in sandboxes | only if you verified it |
| `EEVEE` / `EEVEE Next`, headless | fails with `EGL_BAD_MATCH` / no GL context in a headless container | **no** |

`tools/render_rig.py` defaults to Cycles CPU for this reason.

### Measured timings (2 vCPU, 2 GB RAM sandbox — this is the worst case)

| Resolution / samples | Per view | 8-image set | Notes |
| --- | --- | --- | --- |
| 400² / 8 | ~1 s | — | framing/iteration tests only, **not submittable** |
| 700² / 48 | ~20 s | ~3 min | quick look-dev passes |
| **1600² / 96, denoise on** | **~45 s** | **~6 min** | needs ≥ 3 GB RAM |
| 1600² / 24, `--no-denoise` + post-denoise | ~4 min | **~35 min** | the low-RAM path; clean after post-denoise |
| 2400² / 128, denoise on | ~3–5 min | ~30 min | hero-quality, needs ≥ 4 GB RAM |

**Memory trap you must know about:** OpenImageDenoise allocates ~1.2 GB at 1600². On a 2 GB box the
process is `Killed` (exit 137) **after** the samples finish, and you lose the image. The rig handles
this: it reads `/proc/meminfo` and, below 3 GB RAM, disables OIDN and cleans the image afterwards with
its own low-memory post-denoise (`post_denoise()` in the rig, or `tools/denoise_images.py` standalone —
measured: removes ~70 % of residual error for ~100 MB of RAM). You can force it with `--no-denoise`.

**If a render is still OOM-killed:** render views in smaller batches with `--views 01,02,03`, drop to
`--res 1600 --samples 24 --no-denoise`, and close other processes. Never conclude the scene is broken
and never skip a view — see [NO_STOPPING.md](./NO_STOPPING.md) §3.

---

## 4. Verification checklist (paste this output into your run log)

```bash
blender --version
blender -b --factory-startup --python-expr "import bpy, numpy; print('bpy', bpy.app.version_string, 'numpy', numpy.__version__)"
python3 tools/preflight.py --help | head -3
```

Expected:

```
Blender 4.2.23 LTS
bpy 4.2.23 numpy 1.2x.x
usage: preflight.py ...
```

If any of these fail, **fix it or report the exact command and error**. Do not proceed to modelling
with a broken toolchain and do not stop without reporting.

---

## 5. When installation genuinely cannot work

Only after `bash tools/setup_blender.sh` fails **and** you have captured its output, you may fall back:

1. `pip download bpy==4.2.0` into a **Python 3.11** environment (bpy wheels are version-locked; if you
   have 3.12/3.13 this will not install — that is not an excuse to stop, it is a reason to report the
   Python version alongside the attempt);
2. any other DCC that exports `.glb` (Maya/Modo/Fusion/Houdini/FreeCAD/OpenSCAD) **plus** a headless
   renderer for the PNGs (Blender is still the cheapest route, so try it twice);
3. procedural generation in Python (`trimesh`, `pygltflib`) for simple hard-surface forms, rendered
   with `pyrender`/`filament`/headless three.js.

In every fallback case you must still deliver `.glb` + `.blend`, ≥ 5 renders ≥ 1600², and the
README — and you must state the toolchain in the package README. **A different toolchain is allowed.
A missing deliverable is not.**
