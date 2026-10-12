"""Render actual saved revision, preserve its UI and do not resave."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];scene=bpy.context.scene
original=(scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath)
visibility={o.name:o.hide_render for o in bpy.data.objects}
sys.path.insert(0,str(R/'scripts'))
from transition_v5 import configure
p=json.loads((R/'parameters/transition_v5.json').read_text());cfg=json.loads((R/'parameters/model_config.json').read_text())
configure(cfg,json.loads((R/'parameters/completion.json').read_text()),json.loads((R/'parameters/floor_anchors.json').read_text()),json.loads((R/'parameters/assembly_v3.json').read_text()),p)
z=cfg['transition_v5']['regions'][1]['z_middle_m']
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='TEMP_V13_VERIFY';cam.data.type='ORTHO';scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
for o in bpy.data.objects:
    if o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:o.hide_render=True
for pos,target,scale,name in [((-185,160,72),(-48,0,17),175,'VIEW_33_V13_CLOSED_STREET_SIDE'),
                               ((-110,-165,92),(-42,-50,22),112,'VIEW_34_V13_OPEN_GARDEN_END'),
                               ((-190,60,16),(-63,-2,19),102,'VIEW_35_V13_STONE_ENTRY_NEAR'),
                               ((90,-195,z+4),(0,-35,z),38,'VIEW_36_V13_TRANSITION_RING')]:
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(R/'views'/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath=original
for name,hidden in visibility.items():bpy.data.objects[name].hide_render=hidden
data=cam.data;bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(data)
