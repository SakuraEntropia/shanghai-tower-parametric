"""Inspect the saved v5 scene, refresh delivery texts, save, then inspect again."""
from pathlib import Path
import bpy
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
p=ROOT/'README.md'
t=p.read_text().replace('保存文件须经独立重开检验','模型已在独立进程重开并通过检验')
p.write_text(t)
block=bpy.data.texts.get('00_README_EVIDENCE') or bpy.data.texts.new('00_README_EVIDENCE')
block.clear();block.write(t)
for p in (ROOT/'docs').glob('*v5*'):
    if p.is_file():
        block=bpy.data.texts.get('V5_'+p.name) or bpy.data.texts.new('V5_'+p.name)
        block.clear();block.write(p.read_text())
p=Path(__file__).resolve()
block=bpy.data.texts.get('SCRIPT_'+p.name) or bpy.data.texts.new('SCRIPT_'+p.name)
block.clear();block.write(p.read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
runpy.run_path(str(ROOT/'scripts/inspect_saved.py'),run_name='__main__')
