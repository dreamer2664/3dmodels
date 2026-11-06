#!/usr/bin/env python3
"""make_textures.py — author the wooden-bench texture set with numpy + Pillow.

Outputs (into ../wooden-bench/model/textures/):
  wood_bench_basecolor.png   2048^2  sRGB   tile = 2.0 m (grain, U) x 0.25 m (across, V)
  wood_bench_roughness.png   2048^2  linear
  wood_bench_normal.png      2048^2  linear OpenGL +Y
  iron_cast_basecolor.png    1024^2  sRGB   tile = 0.30 m
  iron_cast_roughness.png    1024^2  linear
  iron_cast_normal.png       1024^2  linear

All noise is periodic (lattice indices wrapped to the octave's grid) so every map
tiles seamlessly — the .blend and the exported .glb share one tiled UV layout.
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "model", "textures"))
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(20261106)


def hash2(ix, iy, period, seed=0):
    """Deterministic hash on a periodic integer lattice -> [0,1)."""
    ix = np.mod(ix + seed * 131, period)
    iy = np.mod(iy + 7 * seed, period)
    h = (ix.astype(np.uint32) * 374761393 + iy.astype(np.uint32) * 668265263
         + np.uint32((seed * 2654435761) & 0xFFFFFFFF))
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h.astype(np.float64) / 4294967296.0)


def value_noise(u, v, freq, seed=0):
    """Seamless value noise on an N x N periodic lattice; u,v in [0,1)."""
    x = u * freq
    y = v * freq
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = x - x0
    fy = y - y0
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    n00 = hash2(x0, y0, freq, seed)
    n10 = hash2(x0 + 1, y0, freq, seed)
    n01 = hash2(x0, y0 + 1, freq, seed)
    n11 = hash2(x0 + 1, y0 + 1, freq, seed)
    a = n00 + sx * (n10 - n00)
    b = n01 + sx * (n11 - n01)
    return a + sy * (b - a)


def fbm(u, v, base_freq, octaves, seed=0, gain=0.5, lac=2.0):
    out = np.zeros((u.shape[0], u.shape[1]), dtype=np.float64)
    amp = 1.0
    tot = 0.0
    f = base_freq
    for i in range(octaves):
        out += amp * value_noise(u, v, int(f), seed + 101 * i)
        tot += amp
        amp *= gain
        f = f * lac
    return out / tot


def save_rgb(name, arr01, srgb=True):
    a = np.clip(arr01, 0, 1)
    if srgb:
        a = np.power(a, 1.0 / 2.2) * 0.985 + 0.006   # never hit pure 0/255
    im = Image.fromarray((a * 255).astype(np.uint8), "RGB")
    im.save(os.path.join(OUT, name), optimize=True)
    print("wrote", name, im.size)


def save_gray(name, arr01):
    a = np.clip(arr01, 0, 1)
    im = Image.fromarray((a * 255).astype(np.uint8), "L")
    im.save(os.path.join(OUT, name), optimize=True)
    print("wrote", name, im.size)


def height_to_normal(h, strength):
    n = h.shape[0]
    dhdx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * n * strength
    dhdy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * n * strength
    # OpenGL +Y up normal map, linear space
    nx = -dhdx
    ny = dhdy
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    r = (nx * inv) * 0.5 + 0.5
    g = (ny * inv) * 0.5 + 0.5
    b = (nz * inv) * 0.5 + 0.5
    return np.stack([r, g, b], axis=-1)


# --------------------------------------------------------------------------- #
# WOOD — quarter-sawn oak, varnished, faintly weathered
# --------------------------------------------------------------------------- #
def build_wood(N=2048):
    ys, xs = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    u = xs / N                      # along the board (tile = 2.0 m)
    v = ys / N                      # across the board (tile = 0.25 m)

    meander = fbm(u, v, 6, 4, seed=3)              # slow wobble of the grain lines
    fine = fbm(u, v, 34, 5, seed=17)
    rings = v * 26.0 + meander * 7.0 + fine * 1.4  # grain bands across V
    band = np.cos(rings * np.pi * 2.0) * 0.5 + 0.5
    porosity = fbm(u, v, 96, 3, seed=41)  # open pores, elongated along the grain
    streak = np.clip(value_noise(u, v, 340, 7) * (0.25 + 0.75 * porosity), 0, 1)

    dark = np.clip(np.power(band, 2.4), 0, 1)                     # thin growth-ring lines
    soft = np.clip(np.power(band, 1.1), 0, 1)

    light = np.array([0.455, 0.335, 0.205])       # varnished oak, mid tone
    mid = np.array([0.330, 0.232, 0.140])
    deep = np.array([0.170, 0.118, 0.070])
    col = light * (1 - soft)[..., None] + mid * soft[..., None]
    col = col * (1 - dark * 0.55)[..., None] + deep * (dark * 0.55)[..., None]
    col = col * (1 - streak * 0.12)[..., None] * (1 + streak * 0.05)[..., None]

    # varnish pooling: broad blotchy sheen difference
    blot = fbm(u, v, 4, 3, seed=55)
    rough = 0.40 + 0.14 * dark + 0.10 * blot + 0.05 * streak      # 0.40-0.69 varnished oak
    height = 0.75 * soft + 0.25 * dark * (1 - porosity * 0.5) + 0.08 * porosity

    save_rgb("wood_bench_basecolor.png", col)
    save_gray("wood_bench_roughness.png", rough)
    save_rgb("wood_bench_normal.png", height_to_normal(height, 0.018))


# --------------------------------------------------------------------------- #
# CAST IRON — sand-cast, weathered, dark oxide with rust freckles
# --------------------------------------------------------------------------- #
def build_iron(N=1024):
    ys, xs = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    u = xs / N
    v = ys / N

    peel = fbm(u, v, 64, 4, seed=11) * 0.6 + fbm(u, v, 160, 3, seed=12) * 0.4  # cast orange-peel
    dents = fbm(u, v, 18, 3, seed=23)
    mottle = fbm(u, v, 7, 4, seed=31)

    oxide = np.array([0.118, 0.118, 0.126])
    worn = np.array([0.235, 0.232, 0.240])
    rust = np.array([0.278, 0.160, 0.078])
    col = oxide * (1 - peel)[..., None] + worn * peel[..., None]
    rustmask = np.clip((mottle - 0.72) * 3.2, 0, 1) * np.clip((dents - 0.45) * 2.0, 0, 1)
    col = col * (1 - rustmask[..., None]) + rust * rustmask[..., None]

    rough = 0.52 + 0.26 * (1 - peel) + 0.06 * dents          # 0.52-0.84 weathered iron
    rough = np.clip(rough, 0, 1)

    height = peel * 0.7 + dents * 0.3
    save_rgb("iron_cast_basecolor.png", col)
    save_gray("iron_cast_roughness.png", rough)
    save_rgb("iron_cast_normal.png", height_to_normal(height, 0.045))


if __name__ == "__main__":
    build_wood()
    build_iron()
    print("texture set done ->", OUT)
