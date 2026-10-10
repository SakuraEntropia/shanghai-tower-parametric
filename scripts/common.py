"""Scene utilities. Display choices never become evidence of real geometry."""
import bpy
import json
from mathutils import Vector

class SceneBuilder:
    def __init__(self, config, parameters, sources):
        self.config, self.parameters, self.sources = config, parameters, sources
        self.project_id = config['project_id']
        self.objects = []
        self.component_results = {}
        self.materials = {}
        self._materials()

    def _materials(self):
        for key, rgba, metal, rough in [
            ('glass',(0.17,0.43,0.57,1),0.38,0.24),
            ('glass_detail',(0.27,0.58,0.70,1),0.18,0.28),
            ('steel',(0.42,0.48,0.53,1),0.7,0.25),
            ('confirmed',(0.21,0.63,0.51,1),0.15,0.42),
            ('derived',(0.83,0.55,0.22,1),0.15,0.5),
            ('unknown',(0.92,0.25,0.12,1),0.0,0.5),
            ('core',(0.60,0.65,0.68,1),0.0,0.72),
            ('guide',(0.35,0.47,0.56,1),0.1,0.45),
            ('text',(0.06,0.11,0.16,1),0.0,0.7),
            ('ground',(0.91,0.93,0.94,1),0.0,0.9),
        ]:
            mat=bpy.data.materials.new('ST_'+key)
            mat.diffuse_color=rgba
            mat.use_nodes=True
            bsdf=mat.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value=rgba
            bsdf.inputs['Metallic'].default_value=metal
            bsdf.inputs['Roughness'].default_value=rough
            if key in ('derived','unknown','guide'):
                bsdf.inputs['Emission Color'].default_value=rgba
                bsdf.inputs['Emission Strength'].default_value=.35
            self.materials[key]=mat

    def collection(self, name):
        c=bpy.data.collections.get(name)
        if c is None:
            c=bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(c)
        c['project_id']=self.project_id
        return c

    def _meta(self, obj, meta):
        defaults={'source_ids':[], 'evidence_level':'待确认', 'formula':'',
                  'uncertainty':'Not established', 'asbuilt_verified':False,
                  'geometry_role':'research_control', 'project_id':self.project_id}
        defaults.update(meta or {})
        for key,value in defaults.items():
            obj[key] = json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) or value is None else value
        self.objects.append(obj)
        return obj

    def mesh(self,name,verts,faces,collection,material,meta,face_attributes=None):
        mesh=bpy.data.meshes.new(name+'_MESH')
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        obj=bpy.data.objects.new(name,mesh)
        self.collection(collection).objects.link(obj)
        if material: mesh.materials.append(self.materials[material] if isinstance(material,str) else material)
        for key, values in (face_attributes or {}).items():
            if len(values)!=len(faces): raise ValueError(f'{key}: face attribute count mismatch')
            attr=mesh.attributes.new(key,'INT','FACE')
            attr.data.foreach_set('value',values)
        return self._meta(obj,meta)

    def lines(self,name,polylines,collection,radius,material,meta):
        curve=bpy.data.curves.new(name+'_CURVE','CURVE')
        curve.dimensions='3D'; curve.resolution_u=1
        curve.bevel_depth=radius; curve.bevel_resolution=1; curve.resolution_u=1
        for pts in polylines:
            if len(pts)<2: continue
            spline=curve.splines.new('POLY'); spline.points.add(len(pts)-1)
            for p,co in zip(spline.points,pts): p.co=(*co,1)
        obj=bpy.data.objects.new(name,curve)
        self.collection(collection).objects.link(obj)
        if material: curve.materials.append(self.materials[material] if isinstance(material,str) else material)
        return self._meta(obj,meta)

    def empty(self,name,location,collection,meta):
        obj=bpy.data.objects.new(name,None)
        obj.empty_display_type='PLAIN_AXES'; obj.empty_display_size=2
        obj.location=location
        self.collection(collection).objects.link(obj)
        return self._meta(obj,meta)

    def box(self,name,center,size,collection,material,meta):
        x,y,z=center; a,b,c=[v/2 for v in size]
        verts=[(x+sx*a,y+sy*b,z+sz*c) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        return self.mesh(name,verts,faces,collection,material,meta)

    def label(self,name,text,location,collection='00_EVIDENCE',size=3,material='text',meta=None):
        curve=bpy.data.curves.new(name+'_TEXT','FONT'); curve.body=text; curve.size=size
        obj=bpy.data.objects.new(name,curve); obj.location=location
        self.collection(collection).objects.link(obj)
        curve.materials.append(self.materials[material])
        return self._meta(obj,meta or {'geometry_role':'annotation','uncertainty':'Display only'})

    def param(self,id):
        return next(a for a in self.parameters['parameters'] if a['id']==id)


def clear_project(project_id):
    for obj in list(bpy.data.objects):
        if obj.get('project_id')==project_id: bpy.data.objects.remove(obj,do_unlink=True)
    for coll in list(bpy.data.collections):
        if coll.get('project_id')==project_id and len(coll.objects)==0: bpy.data.collections.remove(coll)
