"""Render the corrected long side from saved geometry, without resaving it."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
scene=bpy.context.scene
original_camera=scene.camera;original_size=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage);original_path=scene.render.filepath;original_visibility={o.name:o.hide_render for o in bpy.data.objects}
bpy.ops.object.camera_add(location=(-175,-105,90));cam=bpy.context.object;cam.name='TEMP_V11_LONG_SIDE_VIEW'
cam.rotation_euler=(Vector((-43,-4,17))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=148
scene.camera=cam;scene.render.resolution_x=1500;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
for obj in bpy.data.objects:
    if obj.get('geometry_role') in {'research_control','published_elevation_guide_not_floor_plate','inner_zone1_control_not_installed_facade'}:obj.hide_render=True
scene.render.filepath=str(R/'views/VIEW_30_LONG_SIDE_ENTRY_V11.png');bpy.ops.render.render(write_still=True)
scene.camera=original_camera;scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage=original_size;scene.render.filepath=original_path
for name,hidden in original_visibility.items():bpy.data.objects[name].hide_render=hidden
data=cam.data;bpy.data.objects.remove(cam,do_unlink=True);bpy.data.cameras.remove(data)
