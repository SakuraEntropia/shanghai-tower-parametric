"""User-observed aperture counts, snapped to existing lower parent panes.

Coordinates remain candidates: no surveyed all-around aperture map acquired.
"""
import math


def configure(geometry, cfg, crown):
    from crown_pattern_v8 import shared_stations
    rule=crown.get('aperture_layout_v10')
    if not rule:return
    stations=shared_stations(geometry,cfg)
    count=rule['columns'];stride=1+rule['separator_parent_columns']
    width=(count-1)*stride+1
    if count<1 or stride<2:raise ValueError('Separate apertures require retained parent columns')
    pitch=cfg['curtain']['nominal_band_pitch_m'];base=crown['base_z_m']
    vents=[];winds=[];groups=[]
    for face,(center,rows) in enumerate(zip(rule['face_centers_s'],rule['rows_per_face']),1):
        candidates=[i for i in range(len(stations)-width)
                    if stations[i]['s']>0 and stations[i+width]['s']<1
                    and all(b['s']-a['s']>1e-8 for a,b in zip(stations[i:i+width],stations[i+1:i+width+1]))]
        start=min(candidates,key=lambda i:abs((stations[i]['s']+stations[i+width]['s'])/2-center))
        lo,hi=stations[start]['s'],stations[start+width]['s']
        group={'face':face,'columns':count,'rows':rows,'s_min':lo,'s_max':hi,
               'parent_column_count_including_separators':width,
               'evidence_level':'待确认','count_basis':'USER_OBSERVATION_V10',
               'coordinate_basis':'Candidate face centres snapped to existing lower parent grid'}
        groups.append(group)
        old=crown['wind_openings_candidate'][face-1]
        winds.append({**old,'s_min':lo,'s_max':hi,
                      'z_min_m':base+rule['wind_bottom_parent_band']*pitch,
                      'z_max_m':base+(rule['wind_bottom_parent_band']+rule['wind_height_parent_bands'])*pitch,
                      'spans_candidate_glass_bands':rule['wind_height_parent_bands'],
                      'source_ids':list(dict.fromkeys(old['source_ids']+['USER_OBSERVATION_V10']+[rule['spacing_source_id']] if rule.get('spacing_source_id') else old['source_ids']+['USER_OBSERVATION_V10'])),
                      'coordinate_evidence':'User specifies equal group width and3 parent bands; absolute coordinates and band origin remain candidates.'})
        for row in range(rows):
            band=rule['row_starts_parent_band'][row]
            for column in range(count):
                a,b=stations[start+column*stride:start+column*stride+2]
                vents.append({'id':f'UPPER_V10_F{face}_R{row+1}_C{column+1:02d}',
                              'face':face,'row':row+1,'column':column+1,
                              's_min':a['s'],'s_max':b['s'],
                              'z_min_m':base+band*pitch,
                              'z_max_m':base+(band+rule['vent_height_parent_bands'])*pitch,
                              'parent_lower_grid_indices':[a['grid_index'],b['grid_index']],
                              'source_ids':['USER_OBSERVATION_V10','CROWN_GENS_PHOTO_V7']+([rule['spacing_source_id']] if rule.get('spacing_source_id') else []),
                              'evidence_level':'待确认','source_topology_confirmed':False,
                              'spans_candidate_glass_bands':rule['vent_height_parent_bands'],
                              'rule':'11 separated one-column cuts per row; retain earlier two-pane height; 2/2/3 rows. User count, not an as-built aperture schedule.',
                              'uncertainty':'Counts adopted from user observation; face assignment, absolute elevations and widths remain uncalibrated candidates.'})
    crown['vent_openings_candidate']=vents;crown['wind_openings_candidate']=winds
    crown['aperture_groups_v10']=groups


def audit(crown, records):
    """Check cuts in generated parent geometry, not parameter count alone."""
    from crown_pattern_v8 import cut_pane
    area=lambda p:abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2 if len(p)>2 else 0.
    rows=[]
    for opening in crown['vent_openings_candidate']+crown['wind_openings_candidate']:
        overlaps=[]
        for record in records:
            if record.get('aperture_uv_chart')!='global_open_arc_station':continue
            if opening['id'] not in record['hole_ids']:continue
            for poly in record['remaining_uv_polygons']:
                overlaps.append(max(0.,area(poly)-sum(area(p) for p in cut_pane(poly,[opening]))))
        parents=[r for r in records if r.get('aperture_uv_chart')=='global_open_arc_station' and opening['id'] in r['hole_ids']]
        rows.append({'id':opening['id'],'affected_parent_count':len(parents),
                     'remaining_glass_area_inside_hole_sz':sum(overlaps),
                     'passed':bool(parents) and sum(overlaps)<1e-7})
    return rows
