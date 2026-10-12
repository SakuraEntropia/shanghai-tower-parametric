"""Inspect the saved .blend in a separate Blender process."""
import bpy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import validation
from common import glass_material_report
class C: pass
ctx=C();ctx.objects=[o for o in bpy.data.objects if o.get('project_id')=='SHANGHAI_TOWER_EVIDENCE_20261010']
required=['00_README_EVIDENCE','MODEL_USE_AND_VALIDATION','MODEL_IMPLEMENTATION_ASSUMPTIONS','PARAMETERS_JSON','SOURCES_JSON','FLOOR_ANCHORS_JSON','MODEL_CONFIG_JSON','UNCERTAINTY_SUMMARY','PANEL_REGISTRY_JSON','VALIDATION_JSON']
required+=['COMPLETION_PARAMETERS_JSON','COMPLETION_EVIDENCE_AND_LIMITS']
required+=['ASSEMBLY_V3_PARAMETERS','ASSEMBLY_V3_EVIDENCE','ASSEMBLY_V3_PARAMETER_EVIDENCE','ASSEMBLY_V3_REPORT']
v5=bpy.data.objects.get('CROWN_V5_MAIN_DECK_RECT_RECESS_AND_ROUND_APERTURE') is not None
if v5:
    required+=['V5_crown_v5.json','V5_transition_v5.json','V5_11_crown_v5_actual_aerial.md','V5_11_transition_facade_v5.md','V5_11_podium_v5.md','V5_11_v5修正与证据.md']
v6=bpy.context.scene.get('correction_version') in ('v6','v7','v8','v9','v10')
v7=bpy.context.scene.get('correction_version') in ('v7','v8','v9','v10')
if bpy.context.scene.get('correction_version') in ('v8','v9','v10'):required+=['V8_14_v8参数方案与证据.md','V8_site_v8.json']
if bpy.context.scene.get('correction_version') in ('v9','v10'):required+=['V9_15_v9修正方案与证据.md','V9_podium_v9.json','V8_CROWN_PARENT_PANEL_REGISTRY']
if bpy.context.scene.get('correction_version')=='v10':required+=['V10_18_v10孔组入口与街区.md']
if v7:required+=['V7_13_v7参数方案与证据.md','V7_inner_support_v7.json']
if v6:
    required+=['V6_12_crown_v6.md','V6_12_podium_v6.md','V6_12_roof_evidence_v6.md','V6_12_v6修正与证据.md']
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
                         'podium_objects':len([o for o in ctx.objects if 'podium' in o.get('geometry_role','')]),
                         'full_outer_transition_slabs':len([o for o in ctx.objects if o.get('full_outer_transition_plate')]),
                         'crown_cooling_towers':len([o for o in ctx.objects if o.get('geometry_role')=='crown_cooling_tower_candidate'])}
report['passed']=report['passed'] and report['actual_entities']['slabs']==129 and report['actual_entities']['mega_columns']==8
if v5:
    report['passed']=report['passed'] and report['actual_entities']['full_outer_transition_slabs']==16 and report['actual_entities']['crown_cooling_towers']>0
if v6:
    report['actual_glass_materials']=glass_material_report(ctx.objects)
    report['passed']=report['passed'] and bool(report['actual_glass_materials']) and all(row['passed'] for row in report['actual_glass_materials'])
    wind=bpy.data.objects.get('CROWN_V6_270_HORIZONTAL_TURBINE_SHAFTS')
    report['actual_entities']['wind_turbine_shafts']=len(wind.data.splines) if wind else 0
    hall=bpy.data.objects.get('TMD_V6_HALL_126_VISITOR_FLOOR')
    report['actual_entities']['TMD_hall_floor_top_m']=max(v.co.z for v in hall.data.vertices) if hall else None
    report['generation_software_checks_passed']=bool(original.get('software_checks_passed'))
    report['passed']=report['passed'] and report['actual_entities']['wind_turbine_shafts']==270 and report['generation_software_checks_passed']
if bpy.context.scene.get('correction_version') in ('v9','v10'):
    eye=bpy.data.objects.get('TMD_V8_SHANGHAI_EYE_C3_519_JADE_TILE_CANDIDATES');strips=bpy.data.objects.get('TMD_V7_RADIAL_FLAT_LAMELLAE_CLIPPED_AT_CAPSULES')
    count=len({q.value for q in eye.data.attributes['art_tile_id'].data}) if eye else 0
    strip_count=len({q.value for q in strips.data.attributes['canopy_strip_id'].data}) if strips else 0
    x=bpy.data.objects.get('CWSS_V9_THREE_CORNER_PLAN_X_CROSS_RODS');vc=bpy.data.objects.get('TMD_V9_HEAVY_V_COLUMN_GRG_WRAPS')
    report['v9_actual_entities']={'jade_piece_ids':count,'canopy_strip_ids':strip_count,'cross_rods':len(x.data.splines) if x else 0,'V_column_branches':len(vc.data.splines) if vc else 0,'old_podium_geometry_absent':not any(o.name.startswith(('PODIUM_V6_','PODIUM_V7_','PODIUM_V8_')) for o in ctx.objects)}
    report['passed']=report['passed'] and count==519 and strip_count==240 and bool(x) and bool(vc) and report['v9_actual_entities']['old_podium_geometry_absent']
if bpy.context.scene.get('correction_version')=='v10':
    from aperture_layout_v10 import audit
    cp=json.loads(bpy.data.texts['COMPLETION_PARAMETERS_JSON'].as_string())['crown']
    parents=json.loads(bpy.data.texts['V8_CROWN_PARENT_PANEL_REGISTRY'].as_string())
    cut_audit=audit(cp,parents)
    entry=[bpy.data.objects.get(n) for n in ('PODIUM_V10_BROAD_FACE_WHITE_ENTRY_CUT','PODIUM_V10_GLASS_ABOVE_WHITE_ENTRY','PODIUM_V10_RECESSED_ENTRY_GLAZING','PODIUM_V10_WHITE_ENTRY_RETURNS')]
    report['v10_actual_entities']={'vent_count':len(cp['vent_openings_candidate']),'apertures_cut_in_saved_registry':sum(q['passed'] for q in cut_audit),'entry_mesh_faces':[len(o.data.polygons) if o else 0 for o in entry],'green_curve_curbs':len([o for o in ctx.objects if o.name.startswith('SITE_V10_GREEN_CURVE_CURB_')])}
    report['passed']=report['passed'] and len(cut_audit)==80 and all(q['passed'] for q in cut_audit) and all(o and len(o.data.polygons)>0 for o in entry)
(ROOT/'validation/saved_blend_inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
if not report['passed']: raise RuntimeError('Saved blend inspection failed')
