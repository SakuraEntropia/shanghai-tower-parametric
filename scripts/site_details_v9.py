"""Photo/plan-supported street topology; metric marks remain display candidates."""
import math


def smooth_route(points,radius=3,steps=16):
    out=[points[0]]
    for a,b,c in zip(points,points[1:],points[2:]):
        da,dc=math.dist(a,b),math.dist(b,c);d=min(radius,da*.3,dc*.3)
        q=tuple(b[k]+(a[k]-b[k])*d/da for k in range(2));r=tuple(b[k]+(c[k]-b[k])*d/dc for k in range(2))
        for j in range(steps+1):
            t=j/steps;out.append(tuple((1-t)**2*q[k]+2*t*(1-t)*b[k]+t*t*r[k] for k in range(2)))
    out.append(points[-1]);return out


def build_details(ctx,p,meta):
    from site_v8 import xy
    from podium_v9 import _sample
    col='62_STREETS_DERIVED';white=[];yellow=[];crossings=[]
    local={**meta,'geometry_role':'street_photo_marking_candidate','formula':'Plan road centreline; Gensler aerial lane/crosswalk topology; candidate widths, lane count and mark spacing, no surveyed traffic plan.'}
    for road in p['roads']:
        pts=smooth_route([xy(p,q) for q in road['points_px']],p['path_rounding_candidate_m']);length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));width=road['width_candidate_m']
        def point(t,offset):
            c=_sample(pts,t);a,b=_sample(pts,max(0,t-.001)),_sample(pts,min(1,t+.001));dx,dy=b[0]-a[0],b[1]-a[1];d=math.hypot(dx,dy)
            return (c[0]-dy/d*offset,c[1]+dx/d*offset,.018)
        for offset in (-.20,.20):yellow.append([point(i/120,offset) for i in range(121)])
        for offset in (-width/4,width/4):
            pitch=p['road_dash_length_candidate_m']+p['road_dash_gap_candidate_m']
            for i in range(int(length/pitch)):
                a=i*pitch/length;b=min(1,(i*pitch+p['road_dash_length_candidate_m'])/length);white.append([point(a,offset),point(b,offset)])
        for offset in (-width*.45,width*.45):white.append([point(i/120,offset) for i in range(121)])
    ctx.lines('SITE_V9_PHOTO_SUPPORTED_WHITE_LANE_MARK_CANDIDATES',white,col,p['road_mark_width_candidate_m']/2,'ground',local)
    ctx.lines('SITE_V9_DOUBLE_CENTRE_LINE_CANDIDATES',yellow,col,p['road_mark_width_candidate_m']/2,'derived',local)
    for i,q in enumerate(p['crosswalk_centres_candidate_px']):
        x,y=xy(p,q);r=p['roads'][i];a,b=[xy(p,v) for v in (r['points_px'][0],r['points_px'][-1])];dx,dy=b[0]-a[0],b[1]-a[1];d=math.hypot(dx,dy);ux,uy=dx/d,dy/d;w=r['width_candidate_m']
        for j in range(int(w/p['crosswalk_strip_pitch_candidate_m'])-2):
            offset=(j-(int(w/p['crosswalk_strip_pitch_candidate_m'])-3)/2)*p['crosswalk_strip_pitch_candidate_m'];cx,cy=x-uy*offset,y+ux*offset;k=len(crossings)
            poly=[]
            for u,v in ((-1,-1),(1,-1),(1,1),(-1,1)):
                aa=u*p['crosswalk_width_candidate_m']/2;bb=v*p['crosswalk_strip_width_candidate_m']/2;poly.append((cx+ux*aa-uy*bb,cy+uy*aa+ux*bb,.025))
            crossings.append(poly)
    v=[];f=[]
    from podium_v9 import _add
    _add(crossings,v,f);ctx.mesh('SITE_V9_PEDESTRIAN_CROSSING_CANDIDATES',v,f,col,'ground',{**local,'location_evidence':'Aerial source-visible crossings; exact plan-side placement/strip count candidate'})
