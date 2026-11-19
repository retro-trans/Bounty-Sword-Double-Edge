"""Labeled zoom sheet of game glyphs: font_sheet.py out.png idx,idx,... | a-b  [cols]"""
import sys, numpy as np
from PIL import Image, ImageDraw
G = np.load('work/source/glyphs.npy')
spec = sys.argv[2]
if '-' in spec and ',' not in spec:
    a, b = [int(x, 16) for x in spec.split('-')]; idx = list(range(a, b))
else: idx = [int(x, 16) for x in spec.split(',')]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 16
Z = 3; cw = 12*Z+6; chh = 12*Z+12
rows = (len(idx)+cols-1)//cols
im = Image.new('RGB', (cols*cw+30, rows*chh), (30, 30, 30)); dr = ImageDraw.Draw(im)
for k, g in enumerate(idx):
    x = 30+(k % cols)*cw; y = (k//cols)*chh
    if k % cols == 0: dr.text((0, y+12), '%03x' % g, fill=(255, 255, 0))
    t = Image.fromarray(G[g]*255).resize((12*Z, 12*Z), Image.NEAREST)
    im.paste(t, (x, y+10))
    dr.text((x, y), '%x' % (g & 0xf) if cols == 16 else '%03x' % g, fill=(120, 200, 255))
im.save(sys.argv[1])
