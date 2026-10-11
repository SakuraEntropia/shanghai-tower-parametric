"""Generate the traceable Shanghai Tower research scene from factory startup.
Run: Blender --background --factory-startup --python this_file -- --render
"""
import argparse
from pathlib import Path
import json
import sys
import math
import bpy
from mathutils import Vector

SCRIPTS=Path(__file__).resolve().parent
ROOT=SCRIPTS.parent
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
from common import SceneBuilder, clear_project
import geometry
import structure
import curtain_wall
import validation
import core_completion
import inner_completion
import crown_completion
import floors_v3
import crown_detail_v3
import assembly_v3
import notch_v4
import transition_v5


def embed_text(name,text):
    print('EMBED_START',name,len(text),flush=True)
    block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
    block.clear(); block.write(text)
    print('EMBED_DONE',name,flush=True)


def camera(ctx,name,location,target,ortho_scale):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=ortho_scale
    data.clip_start=.1; data.clip_end=5000
    obj=bpy.data.objects.new(name,data); ctx.collection('90_VALIDATION').objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    ctx._meta(obj,{'source_ids':[],'evidence_level':'待确认','geometry_role':'presentation_camera','uncertainty':'Display projection; not original photograph calibration'})
    return obj


def setup(ctx):
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    scene.unit_settings.length_unit='METERS'
    scene.render.engine=ctx.config['display']['render_engine']
    if scene.render.engine=='BLENDER_EEVEE':
        display=ctx.config['display']
        scene.eevee.taa_render_samples=display['render_samples']
        scene.eevee.use_raytracing=display.get('eevee_use_raytracing',False)
        scene.eevee.ray_tracing_options.screen_trace_quality=display.get('eevee_screen_trace_quality',.5)
        scene.eevee.ray_tracing_options.resolution_scale=display.get('eevee_ray_resolution_scale','2')
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world=scene.world or bpy.data.worlds.new('ST_WORLD')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.76,.82,.86,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
    try: scene.view_settings.view_transform='AgX'
    except TypeError: pass
    for name,loc,energy,size in [('ST_KEY',(300,-350,700),5000,450),('ST_FILL',(-300,200,500),3000,400)]:
        data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK'; data.size=size
        obj=bpy.data.objects.new(name,data); obj.location=loc
        obj.rotation_euler=(Vector((0,0,300))-obj.location).to_track_quat('-Z','Y').to_euler()
        ctx.collection('90_VALIDATION').objects.link(obj)
        ctx._meta(obj,{'geometry_role':'presentation_light','uncertainty':'Display only'})
    # Sun provides repeatable lighting for a scene hundreds of metres tall.
    data=bpy.data.lights.new('ST_SUN','SUN'); data.energy=2.5; data.angle=.3
    obj=bpy.data.objects.new('ST_SUN',data); obj.rotation_euler=(.35,-.45,-.5)
    ctx.collection('90_VALIDATION').objects.link(obj);ctx._meta(obj,{'geometry_role':'presentation_light','uncertainty':'Display only'})
    data=bpy.data.lights.new('ST_TMD_HALL_SOFTLIGHT','AREA');data.energy=3000;data.shape='DISK';data.size=8
    obj=bpy.data.objects.new('ST_TMD_HALL_SOFTLIGHT',data);obj.location=(0,0,598)
    ctx.collection('90_VALIDATION').objects.link(obj)
    ctx._meta(obj,{'geometry_role':'presentation_light','uncertainty':'Interior reading light for diagnostic camera; not an installed architectural light fixture'})
    ctx.box('ST_DISPLAY_GROUND',(0,0,-.5),(1000,1000,1),'90_VALIDATION','ground',{'geometry_role':'presentation','uncertainty':'Display top0m; not surveyed site datum'})
    main=camera(ctx,'VIEW_01_TOWER', (780,-1050,430),(0,0,315),720)
    side=camera(ctx,'VIEW_02_SECTION',(0,-1100,315),(0,0,315),690)
    plan=camera(ctx,'VIEW_03_PLAN_45',(0,0,1100),(0,0,45),125)
    detail_origin=ctx.config['curtain']['detail_sample']['location_m']
    detail=camera(ctx,'VIEW_04_CURTAIN_DETAIL',(detail_origin[0]+25,-50,detail_origin[2]+10),(detail_origin[0],0,detail_origin[2]+7),25)
    cwss_origin=ctx.config['structure']['cwss_detail_origin_m']
    node=camera(ctx,'VIEW_05_CWSS',(cwss_origin[0]+18,cwss_origin[1]-25,cwss_origin[2]+14),(cwss_origin[0]+4,cwss_origin[1],cwss_origin[2]+3),24)
    main_near=camera(ctx,'VIEW_06_MAIN_PATTERN',(80,-115,250),(0,-31,250),40)
    crown=camera(ctx,'VIEW_07_CROWN',(170,-200,665),(0,0,586),145)
    inner=camera(ctx,'VIEW_08_INNER',(350,-520,330),(0,0,280),620)
    core_plan=camera(ctx,'VIEW_09_CORE_PLAN',(0,0,1000),(0,0,60),37)
    core=camera(ctx,'VIEW_10_CORE_WALLS',(100,-150,375),(0,0,285),620)
    assembly=camera(ctx,'VIEW_11_ASSEMBLY',(320,-450,350),(0,0,305),690)
    base=camera(ctx,'VIEW_12_GROUNDED_RETAIL',(220,-280,160),(0,0,38),270)
    steel=camera(ctx,'VIEW_13_CWSS_INSTALLED',(115,-150,255),(0,-25,255),85)
    crown_steel=camera(ctx,'VIEW_14_CROWN_ROOF_STEEL',(150,-210,700),(0,0,596),150)
    notch=camera(ctx,'VIEW_15_V_RECESS',(100,-150,260),(0,-24,260),60)
    v_plan=camera(ctx,'VIEW_16_V_PLAN',(0,0,1100),(0,0,45),115)
    aerial=camera(ctx,'VIEW_17_CROWN_AERIAL_V5',(-110,-145,747),(0,0,610),96)
    roof_detail=camera(ctx,'VIEW_18_CROWN_EQUIPMENT_V5',(35,28,725),(0,0,601),56)
    transition=camera(ctx,'VIEW_19_TRANSITION_V5',(105,-145,250),(0,-25,239.4),68)
    hall=camera(ctx,'VIEW_20_TMD_HALL_V6',(3,-13,586.6),(0,-3.8,588.4),23)
    hall.data.type='PERSP';hall.data.lens=22
    hall.location=(2,-14,586.4)
    hall.rotation_euler=(Vector((0,-3.5,590.5))-hall.location).to_track_quat('-Z','Y').to_euler()
    # A local diagnostic projection; exact equipment azimuth is unconfirmed.
    wind_target=(0,-25,574);wind_location=(-65,-95,587)
    if ctx.config.get('completion_enabled'):
        crown_params=json.loads((ROOT/ctx.config['completion_data_file']).read_text())['crown']
        openings=crown_params.get('wind_openings_candidate',[])
        if openings:
            opening=openings[0];s=(opening['s_min']+opening['s_max'])/2;z=(opening['z_min_m']+opening['z_max_m'])/2
            station=min(crown_completion.crown_profile_stations(geometry,ctx.config,160,(s,)),key=lambda p:abs(p['s']-s))
            wind_target=geometry.transform_profile([station['xy']],z,ctx.config)[0]
            wind_location=(wind_target[0]*3,wind_target[1]*3,z+8)
    wind=camera(ctx,'VIEW_21_WIND_BAYS_V6',wind_location,wind_target,33)
    cooling=camera(ctx,'VIEW_22_COOLING_CUTAWAY_V6',(65,-85,580),(0,0,565),45)
    scene.camera=main
    return [main,side,plan,detail,node,main_near,crown,inner,core_plan,core,assembly,base,steel,crown_steel,notch,v_plan,aerial,roof_detail,transition,hall,wind,cooling]


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default=str(ROOT/'parameters/model_config.json'))
    parser.add_argument('--output',default=str(ROOT/'model'))
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--views',default='01,02,04,05,06,07,08,09,10,11,12,13,14')
    args=parser.parse_args(argv)
    cfg=json.loads(Path(args.config).read_text())
    params=json.loads((ROOT/'parameters/parameters.json').read_text())
    sources=json.loads((ROOT/'parameters/sources.json').read_text())
    anchors=json.loads((ROOT/'parameters/floor_anchors.json').read_text())
    if cfg.get('completion_enabled'):
        completion_path=ROOT/cfg['completion_data_file']
        completion=json.loads(completion_path.read_text())
        assembly_path=ROOT/'parameters/assembly_v3.json'
        assembly=json.loads(assembly_path.read_text())
        notch_params=json.loads((ROOT/'parameters/notch_v4.json').read_text())
        cfg['notch_v4']=notch_params
        for component in ('crown_v5','transition_v5'):
            path=ROOT/'parameters'/(component+'.json')
            if path.exists():assembly[component]=json.loads(path.read_text())
        podium_params_path=ROOT/'parameters/podium_v4.json'
        if podium_params_path.exists():assembly['podium_v4']=json.loads(podium_params_path.read_text())
        transition_v5.configure(cfg,completion,anchors,assembly,assembly.get('transition_v5',{}))
    out=Path(args.output).resolve(); out.mkdir(parents=True,exist_ok=True)
    views=out.parent/'views'; views.mkdir(parents=True,exist_ok=True)
    valdir=out.parent/'validation';valdir.mkdir(parents=True,exist_ok=True)
    clear_project(cfg['project_id'])
    for obj in list(bpy.data.objects):
        if obj.name in ['Cube','Camera','Light'] and obj.get('project_id') is None:
            # --factory-startup default furniture; do not remove unrelated user objects.
            if len(bpy.data.objects)<=3: bpy.data.objects.remove(obj,do_unlink=True)
    ctx=SceneBuilder(cfg,params,sources)
    print('SHANGHAI_TOWER_RESEARCH_MODEL',cfg['selected_geometry_version'],flush=True)
    print('UNKNOWN_PARAMETERS',[(a['id'],a['name']) for a in params['parameters'] if a['value'] is None],flush=True)
    print('MODEL_CONVENTIONS',json.dumps(cfg['modeling_conventions'],ensure_ascii=False),flush=True)
    results={}
    results['envelope']=geometry.build_envelope(ctx)
    results['structure']=structure.build_structure(ctx,geometry,anchors)
    cw=curtain_wall.build_curtain_wall(ctx,geometry)
    panel_records=cw.pop('panel_records',[])
    results['curtain']=cw
    if cfg.get('completion_enabled'):
        results['completion']={
            'core':core_completion.build_core(ctx,completion['core']),
            'inner':inner_completion.build_inner(ctx,geometry,completion['inner']),
            'crown':crown_completion.build_crown(ctx,geometry,completion['crown']),
        }
        floors=floors_v3.build_floors(ctx,geometry,completion,anchors,assembly)
        crown_detail=crown_detail_v3.build_crown_detail(ctx,geometry,completion['crown'],assembly)
        if assembly.get('crown_v5'):
            legacy_roof=bpy.data.objects.get('F129_DERIVED_SLAB')
            if legacy_roof:
                legacy_roof.hide_render=True;legacy_roof.hide_viewport=True
                legacy_roof['superseded_by']='CROWN_V5_MAIN_DECK_RECT_RECESS_AND_ROUND_APERTURE'
                legacy_roof['uncertainty']='Archived source-local F/L129 schedule proxy. Visible roof is separately rebuilt from aerial topology with rectangular recess and round aperture; no architectural floor crosswalk resolved.'
            if assembly['crown_v5'].get('version','').startswith('crown-v6'):
                for number in (126,127,128):
                    legacy_floor=bpy.data.objects.get(f'F{number:03d}_DERIVED_SLAB')
                    if legacy_floor:
                        legacy_floor.hide_render=True;legacy_floor.hide_viewport=True
                        legacy_floor['superseded_by']='TMD_V6_HALL_126_VISITOR_FLOOR_AND_OPEN_CHAMBER'
                        legacy_floor['uncertainty']='Archived design-number plate proxy intersects owner-supported L125/126 open TMD cultural volume. Candidate chamber and visitor floor now replace its visible geometry; exact source floor crosswalk remains unconfirmed.'
        physical=assembly_v3.build_assembly(ctx,geometry,completion,assembly)
        results['completion']['V_recess']=notch_v4.build_notch(ctx,geometry,completion,notch_params)
        results['assembly']={'floors':floors,'crown_detail':crown_detail,'physical':physical}
        (valdir/'assembly_report.json').write_text(json.dumps(results['assembly'],ensure_ascii=False,indent=2)+'\n')
        print('V3_ASSEMBLY',floors['slab_count'],physical['load_frame_and_CWSS'],flush=True)
        for obj in ctx.objects:
            if obj.name.startswith('REFERENCE_OPEN_TOP_NO_CROWN_TRIM') or obj.name=='INTERFACE_CROWN_TRIM_UNRESOLVED':
                obj.hide_render=True;obj.hide_viewport=True
    for obj in ctx.objects:
        role=obj.get('geometry_role','')
        if obj.type=='FONT' or role in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'} or 'interface' in role or 'independent_' in role:
            obj.hide_render=True;obj.hide_viewport=True
    (valdir/'panel_registry.json').write_text(json.dumps(panel_records,ensure_ascii=False,indent=2)+'\n')
    cameras=setup(ctx)
    scene=bpy.context.scene
    scene['project_id']=cfg['project_id'];scene['correction_version']='v6'
    scene['accuracy_statement']='Evidence-supported correction v6: real dielectric glass shaders; straight ruled crown net, complete roof oculus, scattered opening candidates, TMD hall and glass-free Windpods bays; source-informed restricted podium glazing/cladding. Exact installed opening/equipment coordinates, optical specifications, hall shape and podium dimensions remain unconfirmed.129 candidate slabs do not resolve actual floor count; no as-built certification.'
    scene['selected_geometry_version']=cfg['selected_geometry_version']
    scene['source_datum_offset_unknown']=True
    report=validation.validate_scene(ctx,geometry,anchors,results)
    summary=dict(report);summary.pop('panel_mesh_diagnostics',None)
    (valdir/'validation_report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (valdir/'panel_mesh_diagnostics.json').write_text(json.dumps(report['panel_mesh_diagnostics'],ensure_ascii=False)+'\n')
    embed_text('00_README_EVIDENCE', (ROOT/'README.md').read_text())
    embed_text('MODEL_USE_AND_VALIDATION', (ROOT/'docs/05_模型使用与核验.md').read_text())
    embed_text('MODEL_IMPLEMENTATION_ASSUMPTIONS', (ROOT/'docs/06_实现参数增补.md').read_text())
    if cfg.get('completion_enabled'):
        embed_text('COMPLETION_PARAMETERS_JSON',completion_path.read_text())
        embed_text('COMPLETION_EVIDENCE_AND_LIMITS',(ROOT/'docs/07_塔冠内层核心补全.md').read_text())
        embed_text('ASSEMBLY_V3_PARAMETERS',assembly_path.read_text())
        embed_text('ASSEMBLY_V3_EVIDENCE',(ROOT/'docs/08_v3实体补齐与精度.md').read_text())
        embed_text('ASSEMBLY_V3_PARAMETER_EVIDENCE',(ROOT/'docs/09_v3参数证据表.md').read_text())
        embed_text('ASSEMBLY_V3_REPORT',json.dumps(results['assembly'],ensure_ascii=False,indent=1))
        embed_text('V4_NOTCH_PARAMETERS',(ROOT/'parameters/notch_v4.json').read_text())
        if podium_params_path.exists():embed_text('V4_PODIUM_PARAMETERS',podium_params_path.read_text())
        for doc in ['10_crown_v4.md','10_podium_v4.md','10_v4修正与图像依据.md']:
            path=ROOT/'docs'/doc
            if path.exists():embed_text('V4_'+doc,path.read_text())
        for path in (ROOT/'parameters').glob('*v5.json'):
            embed_text('V5_'+path.name,path.read_text())
        for path in (ROOT/'docs').glob('*v5*'):
            if path.is_file():embed_text('V5_'+path.name,path.read_text())
        for path in (ROOT/'docs').glob('*v6*'):
            if path.is_file():embed_text('V6_'+path.name,path.read_text())
    embed_text('DESIGN_STAGE2_ARCHIVE', (ROOT/'docs/02_Blender建模方案.md').read_text())
    for name,path in [('PARAMETERS_JSON',ROOT/'parameters/parameters.json'),('SOURCES_JSON',ROOT/'parameters/sources.json'),('FLOOR_ANCHORS_JSON',ROOT/'parameters/floor_anchors.json'),('MODEL_CONFIG_JSON',Path(args.config))]: embed_text(name,path.read_text())
    embed_text('VALIDATION_JSON',json.dumps(summary,ensure_ascii=False,indent=2))
    embed_text('PANEL_REGISTRY_JSON',json.dumps(panel_records,ensure_ascii=False,indent=1))
    embed_text('UNCERTAINTY_SUMMARY',json.dumps(report['uncertainties'],ensure_ascii=False,indent=2))
    for path in SCRIPTS.glob('*.py'): embed_text('SCRIPT_'+path.name,path.read_text())
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=800
            area.spaces.active.region_3d.view_location=Vector((0,0,310))
            area.spaces.active.clip_end=5000
            area.spaces.active.shading.type='MATERIAL'
    bpy.context.view_layer.objects.active=None
    for o in bpy.context.selected_objects: o.select_set(False)
    filepath=out/'shanghai_tower_evidence.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(filepath),compress=True)
    print('SAVED',filepath,flush=True)
    print('SOFTWARE_CHECKS',report['software_checks_passed'],report['geometry_signature'],flush=True)
    if args.render:
        wanted=set(args.views.split(','))
        original_visibility={o.name:o.hide_render for o in ctx.objects}
        sample_collections={'41_CWSS_INDEPENDENT_SPECIMENS','13_CORE_WALL_THICKNESS_SPECIMENS','52_FLOOR_DIAMETER_SPECIMENS','82_HISTORICAL_CWA_2010_SAMPLE'}
        for cam in cameras:
            if cam.name.split('_')[1] not in wanted: continue
            for o in ctx.objects:
                o.hide_render=original_visibility[o.name]
                if o.type=='FONT': o.hide_render=True
                sample=any(c.name in sample_collections for c in o.users_collection)
                if cam.name in ['VIEW_01_TOWER','VIEW_02_SECTION','VIEW_06_MAIN_PATTERN'] and sample: o.hide_render=True
                if cam.name=='VIEW_02_SECTION' and any(c.name.startswith('80_CURTAIN_A_') for c in o.users_collection): o.hide_render=True
                names={c.name for c in o.users_collection}
                if cam.name in {'VIEW_02_SECTION','VIEW_11_ASSEMBLY','VIEW_13_CWSS_INSTALLED','VIEW_14_CROWN_ROOF_STEEL'}:
                    if any(n.startswith(('80_','83_','84_','86_','87_','88_','72_','73_','70_')) for n in names):o.hide_render=True
                    if sample or o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:o.hide_render=True
                if cam.name=='VIEW_22_COOLING_CUTAWAY_V6':
                    if any(n.startswith(('80_','83_','84_','86_','87_','88_','72_','73_','70_')) for n in names) or sample:o.hide_render=True
                if cam.name=='VIEW_08_INNER' and any(n.startswith(('86_','87_')) for n in names):o.hide_render=True
                if cam.name=='VIEW_14_CROWN_ROOF_STEEL' and o.get('geometry_role')=='crown_open_collector_roof_candidate' and o.type=='MESH':o.hide_render=True
                if cam.name=='VIEW_16_V_PLAN':
                    o.hide_render=True
                    if (o.name.startswith('CWA_Z02_') or o.name.startswith('CWA_V_REENTRANT_') or o.name.startswith('ST_B_Z02_')):o.hide_render=False
                if cam.name=='VIEW_12_GROUNDED_RETAIL' and (sample or o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}):o.hide_render=True
                if cam.name=='VIEW_02_SECTION' and any(n.startswith(('83_','84_','72_','73_')) for n in names): o.hide_render=True
                if cam.name=='VIEW_08_INNER' and any(n.startswith(('80_CURTAIN_A_','72_','73_','70_')) for n in names):o.hide_render=True
                if cam.name in {'VIEW_09_CORE_PLAN','VIEW_10_CORE_WALLS'}:
                    o.hide_render=not o.name.startswith('CORE_Z') or '14_CORE_HOLLOW_DERIVED' not in names
                    if cam.name=='VIEW_09_CORE_PLAN' and not o.name.startswith('CORE_Z02_'):o.hide_render=True
                if cam.name in {'VIEW_07_CROWN','VIEW_08_INNER','VIEW_10_CORE_WALLS'} and sample:o.hide_render=True
                if cam.name in {'VIEW_01_TOWER','VIEW_07_CROWN','VIEW_08_INNER','VIEW_06_MAIN_PATTERN'} and o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:
                    o.hide_render=True
                if cam.name=='VIEW_05_CWSS' and any(c.name in {'13_CORE_WALL_THICKNESS_SPECIMENS','52_FLOOR_DIAMETER_SPECIMENS'} for c in o.users_collection): o.hide_render=True
            scene.camera=cam
            scene.render.resolution_x=cfg['display']['image_width']
            scene.render.resolution_y=cfg['display']['image_height']
            if 'DETAIL' in cam.name or 'CWSS' in cam.name or 'PATTERN' in cam.name:
                scene.render.resolution_y=1100
            scene.render.filepath=str(views/(cam.name+'.png'))
            bpy.ops.render.render(write_still=True)
            print('RENDERED',scene.render.filepath,flush=True)
        for o in ctx.objects: o.hide_render=original_visibility[o.name]
        scene.camera=cameras[0]
        bpy.ops.wm.save_as_mainfile(filepath=str(filepath),compress=True)
    if not report['software_checks_passed']: raise RuntimeError('Research geometry checks failed; inspect validation_report.json')

if __name__=='__main__': main()
