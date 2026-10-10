"""Inspect the saved .blend in a separate Blender process."""
import bpy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import validation
class C: pass
ctx=C();ctx.objects=[o for o in bpy.data.objects if o.get('project_id')=='SHANGHAI_TOWER_EVIDENCE_20261010']
required=['00_README_EVIDENCE','MODEL_USE_AND_VALIDATION','MODEL_IMPLEMENTATION_ASSUMPTIONS','PARAMETERS_JSON','SOURCES_JSON','FLOOR_ANCHORS_JSON','MODEL_CONFIG_JSON','UNCERTAINTY_SUMMARY','PANEL_REGISTRY_JSON','VALIDATION_JSON']
required+=['COMPLETION_PARAMETERS_JSON','COMPLETION_EVIDENCE_AND_LIMITS']
required+=['ASSEMBLY_V3_PARAMETERS','ASSEMBLY_V3_EVIDENCE','ASSEMBLY_V3_PARAMETER_EVIDENCE','ASSEMBLY_V3_REPORT']
texts={name: bool(bpy.data.texts.get(name)) for name in required}
collections=[c.name for c in bpy.data.collections if c.get('project_id')=='SHANGHAI_TOWER_EVIDENCE_20261010']
report={'file':bpy.data.filepath,'blender_version':bpy.app.version_string,
        'units':bpy.context.scene.unit_settings.system,'scale_length':bpy.context.scene.unit_settings.scale_length,
        'embedded_texts':texts,'collections':collections,'objects':len(ctx.objects),
        'all_objects_have_source_metadata':all('source_ids' in o and 'uncertainty' in o for o in ctx.objects),
        'geometry_signature':validation.scene_signature(ctx)}
original=json.loads(bpy.data.texts['VALIDATION_JSON'].as_string())
report['signature_matches_generation']=report['geometry_signature']==original['geometry_signature']
report['passed']=all(texts.values()) and report['units']=='METRIC' and report['scale_length']==1 and report['signature_matches_generation'] and report['all_objects_have_source_metadata']
report['actual_entities']={'slabs':len([o for o in ctx.objects if o.get('geometry_role')=='derived_solid_floor_plate_with_core_void']),
                         'mega_columns':len([o for o in ctx.objects if o.name.startswith('MEGA_COLUMN_')]),
                         'installed_CWSS_objects':len([o for o in ctx.objects if o.get('geometry_role')=='installed_CWSS_candidate']),
                         'podium_objects':len([o for o in ctx.objects if o.get('geometry_role')=='podium_retail_mass_and_floors_candidate'])}
report['passed']=report['passed'] and report['actual_entities']['slabs']==129 and report['actual_entities']['mega_columns']==8
(ROOT/'validation/saved_blend_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
if not report['passed']: raise RuntimeError('Saved blend inspection failed')
