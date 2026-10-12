"""Plot actual surviving crown parent polygons from generation diagnostics."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    report=json.loads((R/'validation/validation_report.json').read_text())
    crown=report['components']['completion']['crown']
    polygons=[poly for p in crown['panel_records'] if p['aperture_uv_chart']=='global_open_arc_station' for poly in p['remaining_uv_polygons']]
    fig,ax=plt.subplots(figsize=(15,7))
    ax.add_collection(PolyCollection(polygons,facecolors='#b1c9d5',edgecolors='#648092',linewidths=.22))
    ax.set_xlim(0,1);ax.set_ylim(542,634)
    for g in crown['aperture_groups_v10']:
        ax.text((g['s_min']+g['s_max'])/2,626,f"Face {g['face']}: 11 x {g['rows']}",ha='center',fontsize=12)
        ax.text((g['s_min']+g['s_max'])/2,566.75,'Wind: same width / 3 bands',ha='center',fontsize=9)
    ax.set_xlabel('Existing parent-grid open-arc station s (not metric facade width)')
    ax.set_ylabel('Candidate z [m]')
    ax.set_title('v10: actual crown glass cuts / 22 + 22 + 33 = 77 upper apertures',fontsize=15)
    ax.spines[['right','top']].set_visible(False)
    fig.text(.055,.018,'User-observed counts; candidate absolute positions. 11 holes + 10 retained columns per group. Existing 4.5m parent bands / 2-band vents. Not an as-built elevation.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(R/'views/VIEW_29_CROWN_APERTURE_UNWRAPPED_V10.png',dpi=140);plt.close(fig)

if __name__=='__main__':main()
