"""Photograph-check camera positions; do not alter/resave model geometry."""
import bpy
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];scene=bpy.context.scene
if scene.get('correction_version')!='v14':raise RuntimeError('Historical v14 renderer; use render_v15.py for the current model')
original=(scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath)
visibility={o.name:o.hide_render for o in bpy.data.objects}
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='TEMP_V14_END_VERIFY';cam.data.type='ORTHO';scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
for o in bpy.data.objects:
    if o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:o.hide_render=True
for pos,target,scale,name in [((-60,-125,2),(-41,-74,13),95,'VIEW_37_V14_RAISED_END_FROM_GROUND'),
                               ((-110,-165,92),(-42,-50,22),112,'VIEW_38_V14_TERRACE_AND_TOWER'),
                               ((-185,160,72),(-48,0,17),175,'VIEW_39_V14_CLOSED_STREET_SIDE')]:
    cam.data.type='PERSP' if name.startswith('VIEW_37') else 'ORTHO';cam.data.lens=30
    for object_name,hidden in visibility.items():bpy.data.objects[object_name].hide_render=hidden
    for o in bpy.data.objects:
        if o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:o.hide_render=True
        if name.startswith('VIEW_37') and o.name.startswith(('SITE_V8_PARK_TREE','SITE_V8_TREE_TRUNK')):o.hide_render=True
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(R/'views'/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath=original
for name,hidden in visibility.items():bpy.data.objects[name].hide_render=hidden
data=cam.data;bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(data)
