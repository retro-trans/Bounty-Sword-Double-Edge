"""Identify the game's 12x12 font glyphs by nearest match against MS Gothic's embedded 12px bitmaps.
Writes work/source/font_match.json: [{g, ch, dist, second}]"""
import numpy as np, json
from PIL import Image, ImageFont, ImageDraw
G = np.load('work/source/glyphs.npy')
font = ImageFont.truetype('C:/Windows/Fonts/msgothic.ttc', 12, index=0)
cands = []
for hi in list(range(0x81, 0xa0)) + list(range(0xe0, 0xeb)):
    for lo in range(0x40, 0xfd):
        if lo == 0x7f: continue
        try: ch = bytes([hi, lo]).decode('cp932')
        except Exception: continue
        if len(ch) != 1: continue
        cands.append(ch)
cands = sorted(set(cands))
R = np.zeros((len(cands), 16, 16), dtype=np.uint8)
for i, ch in enumerate(cands):
    im = Image.new('1', (16, 16), 0)
    ImageDraw.Draw(im).text((2, 2), ch, font=font, fill=1)
    R[i] = np.array(im, dtype=np.uint8)
print('cands', len(cands), 'ink avg', R.sum()/len(cands))
# for each glyph, try shifts: place glyph 12x12 at offsets (dx,dy) in 0..4 in 16x16
out = []
Rf = R.reshape(len(cands), -1).astype(np.int16)
for g in range(len(G)):
    if not G[g].any():
        out.append(dict(g=g, ch='', dist=0, second='')); continue
    best = None
    for dy in range(5):
        for dx in range(5):
            P = np.zeros((16, 16), dtype=np.int16); P[dy:dy+12, dx:dx+12] = G[g]
            dist = np.abs(Rf - P.reshape(1, -1)).sum(axis=1)
            idx = np.argsort(dist)[:2]
            cand = (int(dist[idx[0]]), cands[idx[0]], int(dist[idx[1]]), cands[idx[1]])
            if best is None or cand[0] < best[0]: best = cand
    out.append(dict(g=g, ch=best[1], dist=best[0], second=best[3], d2=best[2]))
json.dump(out, open('work/source/font_match.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
import collections
h = collections.Counter(min(o['dist'], 20) for o in out)
print(sorted(h.items()))
