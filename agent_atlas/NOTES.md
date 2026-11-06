# NOTES — agent_atlas

## Decisions (wooden-bench)

- **Interpretation of the brief.** "Wooden bench, iron armrests, very realistic" → a public
  park/street bench: oak slats and timber trestles carry the structure, and the *only* iron is
  the four arched arm rests (two outer + two centre dividers). A generic form, not a replica
  of any manufacturer's product.
- **Scale.** 1.60 m wide (3-seat), seat 0.45 m, top of back 0.85 m, arms at 0.66–0.68 m.
  Ground plane Z = 0, model centred on the origin in X/Y.
- **Materials.** Procedural-free: all detail lives in baked PNG texture sets authored in numpy
  (see scripts/make_textures.py) so the `.glb` is self-contained and identical in every engine.
  1 wood set (2048², box-projected tiled UVs, intentional tiling declared), 1 cast-iron set
  (1024²), 1 plain dark-iron for bolts.
- **UVs.** Planar/box projection in metres from a per-object grain axis, so the wood grain runs
  along every board's long axis and the per-object V-phase breaks the repetition between slats.
  This is deliberate *tiling* UV reuse — not overlapping hero shells; flagged in Limitations.
- **Topology.** Closed boxes + skinned cast-iron straps, 2-segment 2 mm bevels applied, quads.
- **Rendering.** tools/render_rig.py, Cycles CPU, 1600², 96 samples, AgX, dark studio.
  Sandbox has ~2 GB RAM: rig auto-selects the no-OIDN path + post-denoise.
- **Armrest form.** Centreline polyline: riser plate at back → arm forward with a slight rise →
  arched curve → front leg down to a bolt foot on the seat nosing. Rectangular 45 × 18 mm
  strap section, wider/flatter under the palm (section lerp along the path), skinned as quads.

## Dead ends / risks

- EEVEE headless → never attempt (no GL surface). Cycles CPU only. — confirmed working.
- wanted.py prepends `agent_` itself: pass `--agent atlas`, not `agent_atlas`.
  (First run made `agent_agent_atlas`; released + retaken cleanly before any commits.)
