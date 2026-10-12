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
    if 'glass_shader' in ctx.config.get('display',{}):
        from common import glass_material_report
        material_rows=glass_material_report(ctx.objects)
        check('actual_glass_dielectric_transmission',bool(material_rows) and all(row['passed'] for row in material_rows),
              material_rows,'Assigned node shaders use dielectric reflection/refraction; optical values are display candidates, not facade product measurements')
        check('eevee_glass_raytracing_enabled',scene.render.engine!='BLENDER_EEVEE' or scene.eevee.use_raytracing,
              {'engine':scene.render.engine,'raytracing':scene.eevee.use_raytracing},'Software render configuration for transmission preview')
    if results.get('v7_collision'):
        for row in results['v7_collision']['checks']:check(row['name'],row['passed'],row.get('actual'),row.get('meaning','Actual crown steel envelope vs generated glass; not as-built verification'))
    if results.get('assembly',{}).get('physical',{}).get('inner_support_v7'):
        for row in results['assembly']['physical']['inner_support_v7']['checks']:check(row['name'],row['passed'],row.get('actual'),'Generated floor-level support geometry')
    if results.get('assembly',{}).get('physical',{}).get('site_v8'):
        for row in results['assembly']['physical']['site_v8']['checks']:check(row['name'],row['passed'],row.get('actual'),'Published-plan candidate site trace; not survey')
        eye=bpy.data.objects.get('TMD_V8_SHANGHAI_EYE_C3_519_JADE_TILE_CANDIDATES')
        art_bounds=[max(v.co[i] for v in eye.data.vertices)-min(v.co[i] for v in eye.data.vertices) for i in range(3)] if eye else []
        ids={v.value for v in eye.data.attributes['art_tile_id'].data} if eye else set()
        check('v8_artist_nominal_extents_and_519_candidate_tiles',bool(eye) and len(ids)==519 and abs(art_bounds[2]-7.7)<.001 and abs(max(art_bounds[:2])-3.89)<.001,
              {'tile_ids':len(ids),'bounds_m':art_bounds},'Software nominal dimensions/count; shape/tiling is a fit, not fabrication validation')
    if ctx.config.get('podium_v9'):
        e=ctx.config['podium_v9'].get('entrance_v10')
        if ctx.config['podium_v9'].get('side_v13'):
            names=('PODIUM_V13_STREET_STONE_FRAME_BLOCKS','PODIUM_V13_RECESSED_LARGE_ENTRY_GLASS','PODIUM_V13_THREE_STONE_SLOT_WINDOWS','PODIUM_V13_STONE_WINDOW_REVEALS')
            actual={name:len(bpy.data.objects[name].data.polygons) if bpy.data.objects.get(name) else 0 for name in names}
            check('v13_closed_stone_inset_entry_and_slots_present',all(actual.values()),actual,'Street-photo topology; fitted coordinates and modules remain candidates')
        elif e:
            wn=bpy.data.objects.get('PODIUM_V12_LONG_SIDE_STONE_BLOCKS') or bpy.data.objects.get('PODIUM_V10_BROAD_FACE_WHITE_ENTRY_CUT');gn=bpy.data.objects.get('PODIUM_V12_INSET_ENTRANCE_GLASS') or bpy.data.objects.get('PODIUM_V10_GLASS_ABOVE_WHITE_ENTRY');dn=bpy.data.objects.get('PODIUM_V12_ENTRY_STONE_REVEALS') or bpy.data.objects.get('PODIUM_V10_RECESSED_ENTRY_GLAZING')
            actual={'white_faces':len(wn.data.polygons) if wn else 0,'upper_glass_faces':len(gn.data.polygons) if gn else 0,'recessed_glass_faces':len(dn.data.polygons) if dn else 0}
            check('v10_white_cut_entry_and_upper_glass_present',all(actual.values()),actual,'Candidate user-observed entry topology; no recovered final facade elevations')
        cross=bpy.data.objects.get('CWSS_V9_THREE_CORNER_PLAN_X_CROSS_RODS');ring=bpy.data.objects.get('CWSS_INSTALLED_RINGS_CANDIDATE')
        same_z=bool(cross) and all(max(q.co.z for q in sp.points)-min(q.co.z for q in sp.points)<1e-4 for sp in cross.data.splines)
        check('v9_CWSS_three_horizontal_corner_X_pairs_each_ring',bool(cross and ring) and len(cross.data.splines)==6*len(ring.data.splines) and same_z and abs(cross.data.bevel_depth-.03)<1e-6,
              {'cross_members':len(cross.data.splines) if cross else 0,'rings':len(ring.data.splines) if ring else 0,'all_members_horizontal':same_z},'Actual rod axes/count/diameter vs TJAD system; candidate corner coordinates')
        vc=bpy.data.objects.get('TMD_V9_HEAVY_V_COLUMN_GRG_WRAPS');check('v9_heavy_V_hall_supports_generated',bool(vc) and len(vc.data.splines)==24,len(vc.data.splines) if vc else 0,'CIMA/owner-photo topology, candidate12 supports and sections')
        strips=bpy.data.objects.get('TMD_V7_RADIAL_FLAT_LAMELLAE_CLIPPED_AT_CAPSULES');count=len({q.value for q in strips.data.attributes['canopy_strip_id'].data}) if strips else 0
        check('v9_canopy_actual_120_long_120_short_strip_identifiers',count==240,count,'Artist-reported total; individual profiles and positions candidates')
        low=bpy.data.objects.get('PODIUM_V9_LOCAL_PG_POINT_SUPPORTED_GLASS');low_top=max(q.co.z for q in low.data.vertices) if low else 0
        check('v9_podium_generic_perimeter_glass_stops_at_ground_interface',bool(low) and low_top<=4.2001,low_top,'Tall PG arches use shared PR roof-section boundaries, no tall independently guessed perimeter cage')
    world=scene.world
    output=next((n for n in world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None)
    check('world_sky_environment_connected',bool(output and output.inputs['Surface'].is_linked and any(n.type=='TEX_SKY' for n in world.node_tree.nodes)),world.get('environment_model'),'All-direction procedural sky; display weather candidate')
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
    if ctx.config.get('transition_v5',{}).get('horizontal_slits_v13',{}).get('enabled'):
        from corrections_v13 import audit_scene
        current=audit_scene(ctx.objects,ctx.config)
        for q in current['ring_apertures']:
            check(q['id'],q['passed'],q,'Actual A/V glass polygons do not cross candidate ring aperture; all parent columns border both sides')
        check('v13_transition_floor_notches_removed',current['old_slab_notches']==0 and current['restored_full_transition_slabs']==16,current,'Facade clarification: restore full candidate plates; core void and V outline retained')
    if ctx.config.get('podium_v9',{}).get('raised_end_v14',{}).get('enabled'):
        from raised_end_v14 import audit
        q=audit(ctx.objects,ctx.config['podium_v9'])
        check('v14_raised_wrapper_and_recessed_base',q['passed'],q,'Actual wrapper min height / retired ground end glass / no floor-through-soffit; metric work controls remain candidates')
    if ctx.config.get('podium_v9',{}).get('raised_end_v15'):
        from raised_end_v15 import audit
        q=audit(ctx.objects,ctx.config['podium_v9'],ctx.config)
        check('v15_convex_corner_and_local_glass',q['passed'],q,'Actual garden vertices face convex corner; front glass replaces gold/backing. Local phase and dimensions candidates.')
        from corrections_v13 import ring_specs
        holes=ring_specs(ctx.config)
        check('v15_two_midstorey_slits_per_transition',len(holes)==16 and all(len([h for h in holes if h['id'].startswith(r['id']+'_')])==2 for r in ctx.config['transition_v5']['regions']),holes,'Two midheight A/V rings per two-storey region, not at the common slab.')
    finite=all(math.isfinite(x) for obj in ctx.objects if obj.type=='MESH' for v in obj.data.vertices for x in v.co)
    check('finite_mesh_coordinates',finite,None,'No NaN/inf geometry')
    if results.get('assembly',{}).get('crown_detail',{}).get('equipment'):
        crown_z=[]
        for obj in ctx.objects:
            if not obj.name.startswith('CROWN') or obj.hide_render:continue
            if obj.type=='MESH':crown_z.extend((obj.matrix_world@v.co).z for v in obj.data.vertices)
            elif obj.type=='CURVE':
                crown_z.extend((obj.matrix_world@Vector(pt.co[:3])).z for sp in obj.data.splines for pt in sp.points)
        check('v5_visible_crown_controls_within_632m',bool(crown_z) and max(crown_z)<=632.001,
              max(crown_z) if crown_z else None,'Actual base mesh/curve coordinates; small display bevel radii excluded, not surveyed building height')
        deck=bpy.data.objects.get('CROWN_V5_MAIN_DECK_RECT_RECESS_AND_ROUND_APERTURE')
        archived=bpy.data.objects.get('F129_DERIVED_SLAB')
        check('v5_photo_roof_supersedes_legacy_schedule_proxy',deck is not None and archived is not None and archived.hide_render and archived.hide_viewport,
              {'visible_roof':deck.name if deck else None,'archived_schedule_roof_hidden':bool(archived and archived.hide_render)},
              'Avoids duplicate coplanar roof and filling the photograph-derived recess')
        def contains_xy(points,x,y):
            inside=False
            for a,b in zip(points,points[1:]+points[:1]):
                if (a.y>y)!=(b.y>y) and x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x:inside=not inside
            return inside
        covered=[]
        if deck:
            top=max(v.co.z for v in deck.data.vertices)
            top_faces=[[deck.data.vertices[i].co for i in face.vertices] for face in deck.data.polygons
                       if all(abs(deck.data.vertices[i].co.z-top)<.001 for i in face.vertices)]
            for x,y in ((0.,0.),(0.,5.),(0.,-4.)):
                if any(contains_xy(points,x,y) for points in top_faces):covered.append([x,y])
        check('v5_actual_roof_recess_and_round_void_are_unfilled',deck is not None and not covered,
              {'covered_probe_coordinates_m':covered},'Probes real roof mesh opening, not a painted dark rectangle; aperture function remains unconfirmed')
        struts=bpy.data.objects.get('CROWN_RADIAL_CORE_STEEL_FRAME_STRUTS_CANDIDATE')
        beam_top=None;deck_bottom=None
        if struts and deck:
            beam_top=max(pt.co.z for sp in struts.data.splines for pt in sp.points)+struts.data.bevel_depth
            deck_bottom=min(v.co.z for v in deck.data.vertices)
        check('v5_roof_radial_member_envelope_below_deck',beam_top is not None and beam_top<deck_bottom,
              {'highest_member_envelope_m':beam_top,'deck_underside_m':deck_bottom},
              'Actual curve axis plus display radius clears actual deck underside; installed member datum remains candidate')
        cp=results['assembly']['crown_detail']['used_parameters']
        if cp.get('version','').startswith(('crown-v6','crown-v7','crown-v8')):
            old=[bpy.data.objects.get(f'F{n:03d}_DERIVED_SLAB') for n in (126,127,128)]
            check('v6_archived_plates_do_not_slice_TMD_hall',all(o and o.hide_render and o.hide_viewport for o in old),
                  [o.name for o in old if o],'Only duplicate upper design-floor proxies hidden; owner-supported chamber replaces visible geometry')
            net=bpy.data.objects.get('CROWN_V5_STEEP_INNER_NET_CONTINUOUS');errors=[]
            if net:
                for sp in net.data.splines:
                    if len(sp.points)!=cp['collector_net_radial_samples']+1:continue
                    pts=[Vector(pt.co[:3]) for pt in sp.points];axis=pts[-1]-pts[0]
                    errors.extend((v-pts[0]).cross(axis).length/axis.length for v in pts)
            check('v6_actual_exterior_radial_net_generators_straight',bool(errors) and max(errors)<.001,
                  max(errors) if errors else None,'Actual float32 curve points; no lower curved transition; grid dimensions remain photo-fit candidates')
            shafts=bpy.data.objects.get('CROWN_V6_270_HORIZONTAL_TURBINE_SHAFTS')
            check('v6_actual_turbine_unit_count_270',shafts is not None and len(shafts.data.splines)==270,
                  len(shafts.data.splines) if shafts else None,'One actual shaft per candidate turbine; only source count confirmed, row/column positions unconfirmed')
            well=bpy.data.objects.get('CROWN_V6_RECTANGULAR_WELL_FLOOR_FULL_ROUND_OCULUS');blocked=[]
            if well:
                z=max(v.co.z for v in well.data.vertices)
                faces=[[well.data.vertices[i].co for i in f.vertices] for f in well.data.polygons if all(abs(well.data.vertices[i].co.z-z)<.001 for i in f.vertices)]
                cy=cp['deck_aperture_round_center_y_fit_m'];radius=cp['deck_oculus_radius_fit_m']*.65
                probes=[(0,cy)]+[(radius*math.cos(i*math.pi/4),cy+radius*math.sin(i*math.pi/4)) for i in range(8)]
                blocked=[pt for pt in probes if any(contains_xy(face,*pt) for face in faces)]
            check('v6_actual_full_oculus_not_half_circle',well is not None and not blocked,
                  {'blocked_circle_probes':blocked},'Checks full circular void in actual lowered well mesh, including both halves')
            blocked_hatches=[h['center_xy_m'] for h in cp['deck_scattered_apertures_fit'] if any(contains_xy(face,*h['center_xy_m']) for face in top_faces)] if deck else []
            check('v6_scattered_candidates_cut_actual_grating',deck is not None and not blocked_hatches,
                  {'blocked_aperture_centers':blocked_hatches},'Candidate dark-patch interpretations retained as actual editable holes, not textures')
            floor=bpy.data.objects.get('TMD_V6_HALL_126_VISITOR_FLOOR')
            check('v6_hall_visitor_floor_matches_owner_583_4m',floor is not None and abs(max(v.co.z for v in floor.data.vertices)-583.4)<.001,
                  max(v.co.z for v in floor.data.vertices) if floor else None,'Owner nominal level; hall geometry and physical datum alignment remain candidate')
            hall_struts=[]
            if struts:
                for sp in struts.data.splines:
                    pts=[Vector(pt.co[:3]) for pt in sp.points]
                    if pts and cp['tmd_hall_floor_owner_m']-cp['tmd_hall_floor_depth_fit_m']<=pts[0].z<=top:
                        hall_struts.append(min(math.hypot(pt.x,pt.y) for pt in pts)-struts.data.bevel_depth)
            check('v6_actual_radial_steel_clears_TMD_hall',bool(hall_struts) and min(hall_struts)>cp['tmd_hall_radius_fit_m'],
                  {'minimum_member_inner_envelope_radius_m':min(hall_struts) if hall_struts else None,'hall_radius_m':cp['tmd_hall_radius_fit_m']},
                  'Actual curve endpoints plus display radius; removes unsupported candidate steel crossing the public chamber')
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
