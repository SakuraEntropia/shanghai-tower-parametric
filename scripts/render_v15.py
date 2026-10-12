"""Render the saved v15 model without modifying or resaving its geometry."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
scene=bpy.context.scene
if scene.get('correction_version')!='v15':raise RuntimeError('Use the current v15 delivery model')
original=(scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath)
visibility={o.name:o.hide_render for o in bpy.data.objects}
cfg=json.loads(bpy.data.texts['MODEL_CONFIG_JSON'].as_string())
regions=json.loads(bpy.data.texts['ASSEMBLY_V3_REPORT'].as_string())['floors']['transition_regions']
z=regions[1]['z_middle_m']
def rotate(q):
    angle=math.radians(-120);c,s=math.cos(angle),math.sin(angle)
    return (q[0]*c-q[1]*s,q[0]*s+q[1]*c,q[2])
views=[(rotate((-60,-125,2)),rotate((-41,-74,13)),95,'VIEW_41_V15_RAISED_END_FROM_GROUND'),
       (rotate((-110,-165,92)),rotate((-42,-50,22)),132,'VIEW_42_V15_CONVEX_TIP_AND_TERRACE'),
       (rotate((-185,160,72)),rotate((-48,0,17)),175,'VIEW_43_V15_CLOSED_STREET_SIDE'),
       ((90,-195,z+4),(0,-35,z),26,'VIEW_45_V15_TWO_STOREY_RING_SLITS')]
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='TEMP_V15_VERIFY';scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
try:
    for pos,target,scale,name in views:
        cam.data.type='PERSP' if name.startswith('VIEW_41') else 'ORTHO';cam.data.lens=30
        for object_name,hidden in visibility.items():bpy.data.objects[object_name].hide_render=hidden
        for o in bpy.data.objects:
            if o.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:o.hide_render=True
            if name.startswith('VIEW_41') and o.name.startswith(('SITE_V8_PARK_TREE','SITE_V8_TREE_TRUNK')):o.hide_render=True
        cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
        scene.render.filepath=str(R/'views'/(name+'.png'));bpy.ops.render.render(write_still=True)
finally:
    scene.camera,scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath=original
    for name,hidden in visibility.items():bpy.data.objects[name].hide_render=hidden
    data=cam.data;bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(data)
