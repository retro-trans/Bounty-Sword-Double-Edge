"""Render raw bytes as 1bpp tiles: bitview.py file off len tilew tileh out.png [bytes_per_glyph]"""
import sys
from PIL import Image
fn, off, ln, tw, th, out = sys.argv[1], int(sys.argv[2],0), int(sys.argv[3],0), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
d = open(fn,'rb').read()[off:off+ln]
rowb = (tw+7)//8
gb = int(sys.argv[7]) if len(sys.argv)>7 else rowb*th
n = len(d)//gb; cols = 32; rows = (n+cols-1)//cols
img = Image.new('L', (cols*(tw+1), rows*(th+1)), 64); px = img.load()
for g in range(n):
    b = d[g*gb:(g+1)*gb]
    for y in range(th):
        for x in range(tw):
            if gb == rowb*th: bit = b[y*rowb + x//8] >> (7-(x&7)) & 1
            else:
                k = y*tw+x; bit = b[k//8] >> (7-(k&7)) & 1
            px[(g%cols)*(tw+1)+x, (g//cols)*(th+1)+y] = 255 if bit else 0
img.save(out)
