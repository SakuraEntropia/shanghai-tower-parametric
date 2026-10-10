"""Separate software geometry checks from evidence/as-built verification."""
import json
import math
import hashlib
from collections import Counter
from mathutils import Vector


def scene_signature(ctx):
    """Rebuild signature excludes cameras, labels, display matrices and memory IDs."""
    h=hashlib.sha256()
    meshes=0; vertices=0; polygons=0
    for obj in sorted(ctx.objects,key=lambda a:a.name):
        h.update(obj.name.encode())
        if obj.type=='MESH':
            meshes+=1; vertices+=len(obj.data.vertices); polygons+=len(obj.data.polygons)
            for v in obj.data.vertices:
                h.update((','.join(f'{x:.5f}' for x in v.co)+';').encode())
            for f in obj.data.polygons:
                h.update((','.join(str(x) for x in f.vertices)+';').encode())
        elif obj.type=='CURVE':
            for sp in obj.data.splines:
                for pt in sp.points:
                    h.update((','.join(f'{x:.5f}' for x in pt.co[:3])+';').encode())
    return {'sha256_rounded_geometry':h.hexdigest(),'mesh_count':meshes,'vertices':vertices,'polygons':polygons}


def validate_scene(ctx,geometry_module,anchors,results):
    import bpy
    checks=[]
    def check(name,passed,measured,meaning):
        checks.append({'check':name,'passed':bool(passed),'measured':measured,'meaning':meaning,'asbuilt_verified':False})
    scene=bpy.context.scene
    check('metric_scale',scene.unit_settings.system=='METRIC' and scene.unit_settings.scale_length==1.0,
          {'system':scene.unit_settings.system,'scale_length':scene.unit_settings.scale_length},'Software scene units, not datum survey')
    source_ids={s['id'] for s in ctx.sources['sources']}
    bad=[]; missing=[]
    for obj in ctx.objects:
        for key in ['source_ids','evidence_level','formula','uncertainty','asbuilt_verified','geometry_role']:
            if key not in obj: missing.append([obj.name,key])
        ids=json.loads(obj.get('source_ids','[]'))
        if not set(ids)<=source_ids: bad.append([obj.name,ids])
    check('object_evidence_metadata',not missing and not bad,{'objects':len(ctx.objects),'missing':missing,'unresolved_source_ids':bad},'Evidence provenance retained on actual objects')
    for version,data in ctx.config['versions'].items():
        a=geometry_module.curve_state(data['z0_m'],ctx.config,version)
        b=geometry_module.curve_state(data['z1_m'],ctx.config,version)
        dtheta=b['theta_deg']-a['theta_deg']
        check('curve_endpoints_'+version,abs(a['scale']-1)<1e-10 and abs(b['scale']-data['remaining_ratio'])<1e-10 and abs(abs(dtheta)-120)<1e-8,
              {'start':a,'end':b,'rotation_delta_deg':dtheta},'Checks chosen conditional formula, not original BIM or as-built curve')
    control_z=[]
    for obj in ctx.objects:
        if obj.type=='CURVE' and obj.get('geometry_role')=='research_control':
            control_z.extend(float((obj.matrix_world@Vector(pt.co[:3])).z) for sp in obj.data.splines for pt in sp.points)
    check('highest_diagnostic_control_elevation',bool(control_z) and abs(max(control_z)-632)<.001,
          max(control_z) if control_z else None,'632m diagnostic control elevation only; common entrance/design datum and crown contour unverified')
    core_dimensions=[]
    for obj in ctx.objects:
        if obj.type=='MESH' and obj.get('geometry_role')=='core_outer_control_volume_not_walls':
            xs=[v.co.x for v in obj.data.vertices];ys=[v.co.y for v in obj.data.vertices]
            core_dimensions.append({'object':obj.name,'x_m':max(xs)-min(xs),'y_m':max(ys)-min(ys)})
    check('core_30m_outer_control_extent',len(core_dimensions)==4 and all(abs(a['x_m']-30)<.001 and abs(a['y_m']-30)<.001 for a in core_dimensions),
          core_dimensions,'Published design outer extent; these volumes are not modeled concrete walls')
    anchor_errors=[]
    for anchor in anchors['anchors']:
        objs=[o for o in ctx.objects if o.type=='CURVE' and o.get('geometry_role')=='published_elevation_guide_not_floor_plate' and o.get('source_floor_label')==anchor['source_floor_label']]
        if not objs:
            anchor_errors.append({'floor':anchor['source_floor_label'],'error_m':None});continue
        actual_z=float(objs[0].data.splines[0].points[0].co.z)
        anchor_errors.append({'floor':anchor['source_floor_label'],'actual_z_m':actual_z,'source_z_m':anchor['z_m'],'error_m':actual_z-anchor['z_m']})
    check('actual_curve_anchor_elevations',len(anchor_errors)==18 and all(a['error_m'] is not None and abs(a['error_m'])<.001 for a in anchor_errors),
          anchor_errors,'Actual Blender curve coordinates vs published source elevations; source accuracy and datum are separate')
    tube_checks=[]
    for obj in ctx.objects:
        if obj.type!='MESH' or 'outer_diameter_m' not in obj:continue
        verts=obj.data.vertices;n=64
        od=(verts[0].co-verts[n//2].co).length
        expected_od=float(obj['outer_diameter_m'])
        expected_id=json.loads(obj['inner_diameter_m']) if isinstance(obj['inner_diameter_m'],str) else obj['inner_diameter_m']
        id_actual=(verts[2*n].co-verts[2*n+n//2].co).length if expected_id is not None else None
        tube_checks.append({'object':obj.name,'outer_m':od,'expected_outer_m':expected_od,'inner_m':id_actual,'expected_inner_m':expected_id,
                            'passed':abs(od-expected_od)<.0001 and (expected_id is None or abs(id_actual-expected_id)<.0001)})
    check('actual_section_specimen_diameters',bool(tube_checks) and all(a['passed'] for a in tube_checks),tube_checks,
          'Actual generated hollow/solid section diameters; specimens are not installed member locations')
    rows=[]; max_plane=0; max_vertical=0; max_orth=0; badfaces=[]
    for obj in ctx.objects:
        if obj.type!='MESH': continue
        role=obj.get('geometry_role','')
        if 'glass_panel' not in role: continue
        for poly in obj.data.polygons:
            if len(poly.vertices)!=4: continue
            p=[obj.matrix_world@obj.data.vertices[i].co for i in poly.vertices]
            e=[p[(i+1)%4]-p[i] for i in range(4)]
            normal=e[0].cross(e[1])
            if normal.length<1e-10:
                badfaces.append([obj.name,poly.index,'zero_area']); continue
            normal.normalize()
            plane=abs((p[3]-p[0]).dot(normal)); vertical=abs(normal.z)
            orth=max(abs(e[i].normalized().dot(e[(i+1)%4].normalized())) for i in range(4))
            max_plane=max(max_plane,plane); max_vertical=max(max_vertical,vertical); max_orth=max(max_orth,orth)
            lengths=[a.length for a in e]
            rows.append({'object':obj.name,'polygon':poly.index,'plane_error_m':plane,'normal_z_abs':vertical,'orthogonality_cos_abs':orth,'edge_lengths_m':lengths})
    check('glass_panels_are_vertical_planar_rectangles',len(rows)>0 and not badfaces and max_plane<=.001 and max_vertical<=math.sin(math.radians(.01)) and max_orth<=math.sin(math.radians(.01)),
          {'quad_panels':len(rows),'max_plane_error_m':max_plane,'max_normal_z_abs':max_vertical,'max_adjacent_edge_cos_abs':max_orth,'invalid':badfaces[:20]},
          'Numerical geometric rule validation; tolerances are software targets, not glass manufacturing tolerances')
    finite=all(math.isfinite(x) for obj in ctx.objects if obj.type=='MESH' for v in obj.data.vertices for x in v.co)
    check('finite_mesh_coordinates',finite,None,'No NaN/inf geometry')
    parameters=Counter(a['evidence_level'] for a in ctx.parameters['parameters'])
    roles=Counter(obj.get('geometry_role','') for obj in ctx.objects)
    levels=Counter(obj.get('evidence_level','') for obj in ctx.objects)
    check('published_elevation_anchor_count',len(anchors['anchors'])==18,
          [{'source_floor_label':a['source_floor_label'],'z_m':a['z_m'],'normalized_floor_id':a['normalized_floor_id']} for a in anchors['anchors']],
          '18 published monitoring elevations; no complete floor schedule inferred')
    for component,data in results.get('completion',{}).items():
        for entry in data.get('checks',[]):
            check(component+'_'+entry.get('name',entry.get('check','unnamed')),
                  entry['passed'],entry.get('actual',entry.get('measured')),
                  entry.get('scope',entry.get('meaning','Software reconstruction check only')))
    for component,data in results.get('assembly',{}).items():
        for entry in data.get('checks',[]):
            check('assembly_'+component+'_'+entry.get('name',entry.get('check','unnamed')),
                  entry['passed'],entry.get('actual',entry.get('measured')),
                  entry.get('scope',entry.get('meaning','Candidate assembly geometry check, not as-built verification')))
    return {
        'software_checks_passed':all(a['passed'] for a in checks),
        'checks':checks,'panel_mesh_diagnostics':rows,
        'parameter_evidence_counts':dict(parameters),'object_evidence_counts':dict(levels),
        'object_role_counts':dict(roles),'geometry_signature':scene_signature(ctx),
        'components':results,
        'asbuilt_validation':{'status':'NOT_VERIFIED','reason':'No unified as-built curves, complete floor crosswalk, curtain panel/shop drawings, podium boundary or node coordinate schedule'},
        'uncertainties':[a for a in ctx.parameters['parameters'] if a['evidence_level']=='待确认'],
        'software_tolerances':{'planarity_m':.001,'vertical_and_orthogonal_deg':.01},
        'warning':'Software PASS checks the implemented research assumptions only. It cannot validate matching every real building parameter.'
    }
