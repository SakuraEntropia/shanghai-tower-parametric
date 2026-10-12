"""Embed current delivery evidence; independently inspect before/after save."""
from pathlib import Path
import bpy,runpy
R=Path(__file__).resolve().parents[1]
runpy.run_path(str(R/'scripts/inspect_saved.py'),run_name='__main__')
items=[('00_README_EVIDENCE',R/'README.md')]
for version in ('v8','v9','v10','v11'):
 items += [(version.upper()+'_'+p.name,p) for p in (R/'docs').glob('*'+version+'*') if p.is_file()]
 items += [(version.upper()+'_'+p.name,p) for p in (R/'parameters').glob('*'+version+'.json')]
items += [('SCRIPT_'+p.name,p) for p in (R/'scripts').glob('*.py')]
for name,path in items:
 text=bpy.data.texts.get(name) or bpy.data.texts.new(name);text.clear();text.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
runpy.run_path(str(R/'scripts/inspect_saved.py'),run_name='__main__')
