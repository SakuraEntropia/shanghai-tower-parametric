"""Compatibility entry point for the versioned actual-aerial crown builder."""
import json
from pathlib import Path
from crown_v5 import build_detail


def build_crown_detail(ctx, geometry, candidate, assembly):
    params=assembly.get('crown_v5')
    if params is None:
        params=json.loads((Path(__file__).resolve().parents[1]/'parameters/crown_v5.json').read_text())
    return build_detail(ctx,geometry,candidate,assembly,params)
