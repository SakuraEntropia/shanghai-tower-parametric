"""Render an independently opened validated scene without regenerating geometry."""
import argparse,json,sys
from pathlib import Path
import bpy
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from build_shanghai_tower import render_views
class Context:pass
args=argparse.ArgumentParser();args.add_argument('--views',required=True)
p=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ctx=Context();ctx.objects=[o for o in bpy.data.objects if o.get('project_id')=='SHANGHAI_TOWER_EVIDENCE_20261010']
cfg=json.loads(bpy.data.texts['MODEL_CONFIG_JSON'].as_string());names=p.views.split(',')
cameras=[next(o for o in bpy.data.objects if o.type=='CAMERA' and o.name.startswith('VIEW_'+n+'_')) for n in names]
render_views(ctx,cameras,cfg,set(names),Path(bpy.data.filepath),R/'views')
