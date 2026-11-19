"""Build glyph-index -> Unicode table by matching the game font against MS Gothic 12px bitmaps.
Writes work/glossary/charmap.json: list of {idx, ch, dist, alt}."""
import sys, json
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import font as F

win = open('work/source/disc/BIN/WIN.BIN', 'rb').read()
px = F.load_planes(win)
G = np.array([np.array(F.glyph(px, g), dtype=np.int8) for g in range(F.NGLYPH)])

ft = ImageFont.truetype(r'C:\Windows\Fonts\msgothic.ttc', 12, index=0)
cands = []
for row in range(0x21, 0x75):
    for col in range(0x21, 0x7f):
        try:
            ch = bytes([0x1b, 0x24, 0x42, row, col]).decode('iso2022_jp')
        except Exception:
            continue
        cands.append(ch)
cands += [chr(c) for c in range(0x21, 0x7f)]
imgs = []
for ch in cands:
    im = Image.new('1', (12, 12), 0)
    ImageDraw.Draw(im).text((0, 0), ch, font=ft, fill=1)
    imgs.append(np.array(im, dtype=np.int8))
C = np.array(imgs)
print(len(cands), 'candidates; sample ink', C[100].sum(), C[2000].sum())

def best(g):
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            s = np.roll(np.roll(g, dy, 0), dx, 1)
            d = np.abs(C - s).sum(axis=(1, 2))
            for i in np.argsort(d)[:3]:
                out.append((int(d[i]), cands[i]))
    out.sort()
    seen = []; res = []
    for d, c in out:
        if c not in seen:
            seen.append(c); res.append((d, c))
    return res[:3]

tbl = []
for g in range(F.NGLYPH):
    if G[g].sum() == 0:
        tbl.append(dict(idx=g, ch=' ' if g == 0 else '', dist=0, alt=[])); continue
    b = best(G[g])
    tbl.append(dict(idx=g, ch=b[0][1], dist=b[0][0], alt=[[d, c] for d, c in b[1:]]))
json.dump(tbl, open('work/glossary/charmap_auto.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
import collections
h = collections.Counter(min(t['dist'], 20) for t in tbl)
print(sorted(h.items()))
