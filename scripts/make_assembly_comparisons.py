"""Source/actual-render diagnostic boards for assembly v3; no image synthesis."""
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'views'
OUT.mkdir(exist_ok=True)
FONT = font_manager.findfont('DejaVu Sans')
BOLD = font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans', weight='bold'))


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def comparison(name, title, source_path, render_path, left_title, right_title, foot, crop=None):
    canvas = Image.new('RGB', (2500, 1640), '#ffffff')
    draw = ImageDraw.Draw(canvas)
    draw.text((45, 25), title, font=font(35, True), fill='#172b3d')
    draw.line((45, 87, 2455, 87), fill='#b2c0ca', width=2)
    boxes = [(45, 155, 1205, 1385), (1260, 155, 2455, 1385)]
    for path, label, box, source in zip((source_path, render_path), (left_title, right_title), boxes, (True, False)):
        draw.text((box[0], 109), label, font=font(24, True), fill='#233746')
        picture = Image.open(ROOT / path).convert('RGB')
        if source and crop:
            picture = picture.crop(crop)
        picture = ImageOps.contain(picture, (box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
        canvas.paste(picture, (box[0] + (box[2] - box[0] - picture.width) // 2,
                               box[1] + (box[3] - box[1] - picture.height) // 2))
        draw.rectangle(box, outline='#d6dfe5', width=2)
    draw.rectangle((45, 1410, 2455, 1603), fill='#f6eeeb')
    y = 1429
    for paragraph in foot:
        for line in wrap(paragraph, 154):
            draw.text((62, y), line, font=font(22), fill='#733d30')
            y += 32
    canvas.save(OUT / name)
    print(name)


if __name__ == '__main__':
    comparison('COMPARE_V3_CROWN_ROOF_STEEL.png',
               'Shanghai Tower / crown roof and steel assembly comparison',
               'references/new_crown/NTUA_original-002.png',
               'views/VIEW_14_CROWN_ROOF_STEEL.png',
               'Primary design source / TT 2014 Fig9',
               'Actual Blender v3 render / candidate geometry',
               ['Source: designer-authored NTUA proceedings, Fig9 (2014 file). Its original/current models document design development; neither is an as-built coordinate set.',
                'Model: open crown, candidate collector roof and truss topology. Rim mapping, member positions and sections remain derived/display parameters.',
                'Comparison checks spatial relationships only. It does not establish exact alignment with the real building or final fabrication details.'])
    comparison('COMPARE_V3_FLOORS_FRAME.png',
               'Shanghai Tower / floor slabs, core and outer frame comparison',
               'references/new_inner/Ding-03.png',
               'views/VIEW_11_ASSEMBLY.png',
               'Primary design source / Ding 2010 Fig5',
               'Actual Blender v3 render / editable assembly',
               ['Source: Tongji design-team paper (2010), printed p124 Fig5. Cropped orthographic structural section; no stated construction-drawing scale.',
                'Model: independent solid slabs with core voids, stepped circular radii and frame interfaces. S13 anchors stay exact; intervening levels are interpolated candidates.',
                '129 is the number of modeled candidate slabs, NOT a confirmed real floor count. Source-local F/L labels and physical slab-top elevations remain unresolved.'],
               crop=(1200, 100, 2060, 1490))
