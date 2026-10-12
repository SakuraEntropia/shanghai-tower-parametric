"""Embed current delivery evidence; independently inspect before/after save."""
from pathlib import Path
import bpy,runpy
R=Path(__file__).resolve().parents[1]
if bpy.context.scene.get('correction_version')=='v12':
 import json
 p=json.loads((R/'parameters/podium_v9.json').read_text())
 bpy.context.scene['accuracy_statement']='v12: open upper balcony; smaller recessed glass entry in separate stone blocks; detailed candidate glass/stainless canopy; p29 XY with unsurveyed grade mounds and two sunken courts; roof disc radius15.3m candidate, nominal35m TMD hall retained. 77 crown apertures with2 retained columns,3-band wind bays and16 candidate transition slab notches retained. No final facade/RC/shop/elevation CAD or roof disc survey; not construction/as-built precision.'
 o=bpy.data.objects.get('PODIUM_V9_LIMITED_PS_OPAQUE_FRONT_BAND')
 if o:o['tile_module_evidence']=str(p['opaque_tiles_v11'])+'; candidate stone module, no PS shop schedule recovered'
 site=json.loads((R/'parameters/site_v8.json').read_text())
 for obj in bpy.data.objects:
  if obj.name.startswith(('SITE_V8_GREEN_BAND_','SITE_V8_PARK_PATH_','SITE_V8_PARK_TREE','SITE_V8_TREE_TRUNK','SITE_V8_BENCH','SITE_V10_GREEN','SITE_V8_STREET_LAMP')):
   obj['source_ids']=json.dumps(list(dict.fromkeys(json.loads(obj['source_ids'])+['USER_OBSERVATION_V12'])))
   obj['height_rule_v12']='Candidate p29 green-band elliptical mounds with smooth zero boundary; shared ground function for path/plant/fixture; no surveyed heights.'
   obj['height_parameters_v12']=json.dumps(site['levels_v12'])
runpy.run_path(str(R/'scripts/inspect_saved.py'),run_name='__main__')
items=[('00_README_EVIDENCE',R/'README.md')]
items.append(('SOURCES_JSON',R/'parameters/sources.json'))
items.append(('MODEL_CONFIG_JSON',R/'parameters/model_config.json'))
for version in ('v8','v9','v10','v11','v12','v13','v14','v15'):
 items += [(version.upper()+'_'+p.name,p) for p in (R/'docs').glob('*'+version+'*') if p.is_file()]
 items += [(version.upper()+'_'+p.name,p) for p in (R/'parameters').glob('*'+version+'.json')]
items += [('SCRIPT_'+p.name,p) for p in (R/'scripts').glob('*.py')]
for name,path in items:
 text=bpy.data.texts.get(name) or bpy.data.texts.new(name);text.clear();text.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
runpy.run_path(str(R/'scripts/inspect_saved.py'),run_name='__main__')
