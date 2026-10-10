# Tower Crown, Inner Skin and Core Completion Implementation Plan

**Goal:** Extend the delivered evidence model with dimensioned hollow core walls, piecewise cylindrical inner skin and a trimmed open crown supported by primary drawings.
**Architecture:** A new `completion.py` module consumes `parameters/completion.json`, emits separate core/inner/crown collections and returns numeric diagnostics. Old control volumes remain available but hidden; published source facts are never overwritten. Each new object retains locator, method and uncertainty; no as-built certification.
**Tech Stack:** Blender bpy, standard Python; Pillow/Numpy for source measurement and QA figures.
**Spec:** User follow-up explicitly requests crown, correct inner layer and core, retaining the original evidence rules.

## Global Constraints
- Metric 1:1; Z up; existing local axis, zero datum and external geometry version retained.
- Candidate source stages remain separate; uncertainties must accompany derived geometry.
- Missing doors, rebar, glass exceptions and unmeasured crown nodes remain unmodeled.

## Tasks
- [x] Read primary crown/inner/core source drawings, archive reference pages and measurement inputs.
- [x] Add source registry entries and `completion.json` carrying coordinates, heights, methods and error ranges.
- [x] Implement `build_completion(ctx, geometry)` in `scripts/completion.py`: hollow wall solids from measured layout; non-twisting cylinders by zone; truncated external crown with geometry subpanels and open top.
- [x] In `build_shanghai_tower.py`, invoke completion after original components; hide superseded controls, embed new evidence/config and add core/crown QA cameras.
- [x] Run geometry tests, validate generated core voids/zone changes, inner radii/clearance and crown extrema/open edge; reopen saved blend.
- [x] Render three QA views and source comparisons, update docs and regenerate manifest/ZIP.

## Numeric QA contract
`results["completion"]` returns `core` (`zones`, wall dimensions and layout traces), `inner` (`zones`, radii, grid assumption), `crown` (`min_trim_z`, `max_trim_z`, open boundary and source-frame mapping), plus `checks` (name/passed/actual/scope). Scene checks append these checks and only report software correctness. A hollow nine-cell lower core must contain voids at measured cell centers; inner radii may not twist with A; crown highest point must equal its versioned target while top remains uncapped.
