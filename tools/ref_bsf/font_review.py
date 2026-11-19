"""Review sheet: game glyph (3x) + the matched character drawn large. font_review.py out_prefix mindist"""
import sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
G = np.load('work/source/glyphs.npy')
m = json.load(open('work/source/font_match.json', encoding='utf-8'))
mind = int(sys.argv[2])
items = [o for o in m if o['dist'] >= mind and not (0x6d <= o['g'] <= 0x140)]
print(len(items))
big = ImageFont.truetype('C:/Windows/Fonts/msgothic.ttc', 30, index=0)
small = ImageFont.load_default()
cols, per = 10, 60
for page in range(0, len(items), per):
    chunk = items[page:page+per]
    cw, ch = 86, 62
    im = Image.new('RGB', (cols*cw, ((len(chunk)+cols-1)//cols)*ch), (30, 30, 30)); dr = ImageDraw.Draw(im)
    for k, o in enumerate(chunk):
        x = (k % cols)*cw; y = (k//cols)*ch
        im.paste(Image.fromarray(G[o['g']]*255).resize((36, 36), Image.NEAREST), (x+2, y+14))
        dr.text((x+44, y+16), o['ch'], font=big, fill=(120, 255, 120))
        dr.text((x+2, y+1), '%03x d%d' % (o['g'], o['dist']), font=small, fill=(255, 255, 0))
    im.save('%s_%02d.png' % (sys.argv[1], page//per))
