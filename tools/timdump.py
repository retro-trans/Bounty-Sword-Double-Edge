"""Scan a file for PS1 TIM images and dump them as PNG (for locating fonts / UI graphics)."""
import sys, os, struct
from PIL import Image

def c15(v):
    return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3)

def parse_tim(d, o):
    if d[o:o+4] != b'\x10\x00\x00\x00': return None
    fl = struct.unpack('<I', d[o+4:o+8])[0]
    if fl not in (0, 1, 2, 3, 8, 9): return None
    p = o + 8; clut = None; info = {}
    if fl & 8:
        ln, x, y, w, h = struct.unpack('<IHHHH', d[p:p+12])
        if ln != 12 + w*h*2 or w*h > 4096: return None
        clut = [struct.unpack('<%dH' % w, d[p+12+i*w*2:p+12+(i+1)*w*2]) for i in range(h)]
        info['clut'] = (x, y, w, h); p += ln
    ln, x, y, w, h = struct.unpack('<IHHHH', d[p:p+12])
    if ln != 12 + w*h*2 or w == 0 or h == 0 or w > 1024 or h > 512: return None
    info.update(off=o, bpp=fl & 3, x=x, y=y, w=w, h=h, data=p+12, end=p+ln, clutdata=clut)
    return info

def render(d, t, ci=0, gray=False):
    w, h, bpp = t['w'], t['h'], t['bpp']
    raw = d[t['data']:t['end']]
    if bpp == 0:
        W = w*4; pal = t['clutdata'][ci][:16] if t['clutdata'] and not gray else None
        im = Image.new('RGB', (W, h)); px = im.load()
        for y in range(h):
            for x in range(W):
                b = raw[y*w*2 + x//2]; v = (b >> 4) if x & 1 else (b & 15)
                px[x, y] = c15(pal[v]) if pal else (v*17,)*3
    elif bpp == 1:
        W = w*2; pal = t['clutdata'][ci] if t['clutdata'] else None
        im = Image.new('RGB', (W, h)); px = im.load()
        for y in range(h):
            for x in range(W):
                v = raw[y*w*2 + x]
                px[x, y] = c15(pal[v]) if pal else (v,)*3
    else:
        im = Image.new('RGB', (w, h)); px = im.load()
        for y in range(h):
            for x in range(w):
                px[x, y] = c15(struct.unpack('<H', raw[(y*w+x)*2:(y*w+x)*2+2])[0])
    return im

if __name__ == '__main__':
    path, out = sys.argv[1], sys.argv[2]
    gray = len(sys.argv) > 3
    d = open(path, 'rb').read()
    os.makedirs(out, exist_ok=True)
    o = 0; n = 0
    while True:
        o = d.find(b'\x10\x00\x00\x00', o)
        if o < 0: break
        t = parse_tim(d, o)
        if t:
            print('%08x bpp=%d vram=(%d,%d) %dx%d clut=%s' % (o, t['bpp'], t['x'], t['y'], t['w'], t['h'], t.get('clut')))
            render(d, t, gray=gray).save(os.path.join(out, '%s_%08x.png' % (os.path.basename(path), o)))
            o = t['end']; n += 1
        else:
            o += 4
    print(n, 'TIMs')
