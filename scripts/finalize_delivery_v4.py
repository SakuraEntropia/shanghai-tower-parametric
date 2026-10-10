"""Refresh current delivery text blocks; preserve generated geometry."""
from pathlib import Path
import bpy,runpy
ROOT=Path(__file__).resolve().parent.parent
for name,path in [('00_README_EVIDENCE',ROOT/'README.md'),('SCRIPT_finalize_delivery_v4.py',Path(__file__))]:
 block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
 block.clear();block.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/shanghai_tower_evidence.blend'),compress=True)
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
