"""TIM decode helpers + dump every TIM in a file to PNG."""
import struct, sys, os
from PIL import Image

def c15(v):
    r = (v & 31) << 3; g = ((v >> 5) & 31) << 3; b = ((v >> 10) & 31) << 3
    return (r, g, b)

def parse(d, o):
    """return dict or None"""
    if d[o:o+4] != b'\x10\x00\x00\x00': return None
    fl = struct.unpack_from('<I', d, o+4)[0]
    if fl & ~0xf: return None
    bpp = fl & 3; p = o + 8; clut = None; cl = None
    if fl & 8:
        ln, x, y, w, h = struct.unpack_from('<IHHHH', d, p)
        if ln != 12 + w*h*2 or w*h > 4096: return None
        clut = struct.unpack_from('<%dH' % (w*h), d, p+12); cl = (x, y, w, h)
        p += ln
    if p + 12 > len(d): return None
    ln, x, y, w, h = struct.unpack_from('<IHHHH', d, p)
    if ln != 12 + w*h*2 or w == 0 or h == 0 or w > 1024 or h > 512: return None
    return dict(off=o, bpp=bpp, clut=clut, clutpos=cl, x=x, y=y, w=w, h=h, pix=p+12, end=p+ln)

def to_image(d, t, pal=0, gray=False):
    w, h = t['w'], t['h']; px = d[t['pix']:t['end']]
    if t['bpp'] == 0:
        W = w*4; img = Image.new('RGB', (W, h)); pp = img.load()
        for y in range(h):
            for x in range(W):
                b = px[y*w*2 + x//2]; v = (b >> 4) if x & 1 else (b & 15)
                if gray or not t['clut']: pp[x, y] = (v*17,)*3
                else: pp[x, y] = c15(t['clut'][pal*16+v])
    elif t['bpp'] == 1:
        W = w*2; img = Image.new('RGB', (W, h)); pp = img.load()
        for y in range(h):
            for x in range(W):
                v = px[y*w*2+x]
                pp[x, y] = c15(t['clut'][v]) if t['clut'] and not gray else (v,)*3
    else:
        W = w; img = Image.new('RGB', (W, h)); pp = img.load()
        for y in range(h):
            for x in range(W):
                pp[x, y] = c15(struct.unpack_from('<H', px, (y*w+x)*2)[0])
    return img

def find_all(d):
    out = []; o = 0
    while True:
        o = d.find(b'\x10\x00\x00\x00', o)
        if o < 0: break
        t = parse(d, o)
        if t: out.append(t); o = t['end']
        else: o += 4 if o % 4 == 0 else 1
    return out

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read(); outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    for t in find_all(d):
        print(f"{base} off {t['off']:7x} bpp {t['bpp']} fb ({t['x']},{t['y']}) {t['w']}x{t['h']} clut {t['clutpos']}")
        to_image(d, t, gray=('gray' in sys.argv)).save(os.path.join(outdir, f"{base}_{t['off']:07x}.png"))
