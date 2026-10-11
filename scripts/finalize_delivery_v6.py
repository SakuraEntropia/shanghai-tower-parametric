"""Independently inspect saved v6, refresh delivery evidence, save and inspect again."""
from pathlib import Path
import bpy,runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
for name,path in [('00_README_EVIDENCE',ROOT/'README.md')]+[('V6_'+p.name,p) for p in (ROOT/'docs').glob('*v6*') if p.is_file()]:
    block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
    block.clear();block.write(path.read_text())
for p in (ROOT/'scripts').glob('*.py'):
    block=bpy.data.texts.get('SCRIPT_'+p.name) or bpy.data.texts.new('SCRIPT_'+p.name)
    block.clear();block.write(p.read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
