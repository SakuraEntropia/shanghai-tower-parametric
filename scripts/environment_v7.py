"""Self-contained full-sphere sky; no claim of captured Shanghai weather."""
import math

def setup_world(scene,p):
    world=scene.world;tree=world.node_tree;tree.nodes.clear()
    output=tree.nodes.new('ShaderNodeOutputWorld');output.location=(800,0)
    bg=tree.nodes.new('ShaderNodeBackground');bg.location=(600,0);bg.inputs['Strength'].default_value=p['strength']
    sky=tree.nodes.new('ShaderNodeTexSky');sky.location=(-200,100)
    allowed={i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items}
    sky.sky_type='SINGLE_SCATTERING' if 'SINGLE_SCATTERING' in allowed else 'NISHITA'
    sky.sun_elevation=math.radians(p['sun_elevation_deg']);sky.sun_rotation=math.radians(p['sun_rotation_deg'])
    sky.air_density=p['air_density'];sky.ozone_density=p['ozone_density'];sky.sun_disc=True;sky.sun_size=math.radians(.545)
    if hasattr(sky,'aerosol_density'):sky.aerosol_density=p['dust_density']
    elif hasattr(sky,'dust_density'):sky.dust_density=p['dust_density']
    coord=tree.nodes.new('ShaderNodeTexCoord');coord.location=(-800,-240)
    noise=tree.nodes.new('ShaderNodeTexNoise');noise.location=(-590,-240);noise.inputs['Scale'].default_value=p['cloud_noise_scale'];noise.inputs['Detail'].default_value=4
    ramp=tree.nodes.new('ShaderNodeValToRGB');ramp.location=(-360,-240)
    ramp.color_ramp.elements[0].position=.49;ramp.color_ramp.elements[1].position=.75
    ramp.color_ramp.elements[1].color=(p['cloud_coverage'],)*3+(1,)
    mix=tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.location=(340,0);mix.inputs[2].default_value=(.55,.67,.78,1)
    tree.links.new(coord.outputs['Normal'],noise.inputs['Vector']);tree.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);tree.links.new(ramp.outputs['Color'],mix.inputs[0])
    tree.links.new(sky.outputs['Color'],mix.inputs[1]);tree.links.new(mix.outputs['Color'],bg.inputs['Color']);tree.links.new(bg.outputs['Background'],output.inputs['Surface'])
    world['environment_model']='Single-scattering/Nishita physical sky + procedural cloud field'
    world['evidence_level']='待确认（展示）';world['uncertainty']=p['uncertainty']
