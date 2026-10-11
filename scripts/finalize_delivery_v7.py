"""Refresh embedded delivery records without changing generated geometry."""
from pathlib import Path
import bpy,runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
items=[('00_README_EVIDENCE',ROOT/'README.md')]
items += [('V7_'+p.name,p) for p in (ROOT/'docs').glob('*v7*') if p.is_file()]
items += [('V7_'+p.name,p) for p in (ROOT/'parameters').glob('*v7.json')]
items += [('SCRIPT_'+p.name,p) for p in (ROOT/'scripts').glob('*.py')]
for name,path in items:
    block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
    block.clear();block.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
