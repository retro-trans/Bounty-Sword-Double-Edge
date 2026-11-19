"""English font for the VWF: Silver (CC BY 4.0, Poppy Works) drawn into the game's font page.

The font page (WINBIN entry 0, chunk at +0x48, 20-byte header, 0x8000 bytes of 4bpp 256x256)
holds 12x12 cells; glyph g uses bit plane g % 3 of cell g // 3 (21 cells per row).

    ENC          char -> glyph code
    widths()     glyph code -> advance in pixels (only for redrawn glyphs)
    patch(page)  returns the font page bytes with the English glyphs drawn
    encode(s)    English string -> list of glyph codes (raises on a character without a glyph)

    python tools/enfont.py preview work/ui/font/en_cells.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTF = os.path.join(ROOT, 'tools', 'fonts', 'silver', 'Silver.ttf')
TOP = 2          # Silver row drawn at cell row 0 (ASCII spans rows 2..13 at size 19, drawn at y=0)

ENC = {}
for i, c in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop'):
    ENC[c] = 0x6D + i
for i, c in enumerate('qrstuvwxyz'):
    ENC[c] = 0x4BC + i
ENC.update({'!': 0x466, '?': 0x467, ':': 0x4A7, '(': 0x369, ')': 0x36A, '/': 0x04, '&': 0x0C, '%': 0x0B,
            '+': 0x07, '-': 0x08, '=': 0x09, '~': 0x371, ',': 0x524,
            # new glyphs in the five unused filler cells
            '.': 0x526, "'": 0x527, '"': 0x528, ';': 0x529, ' ': 0x52A})
SPACE_ADV = 4


def _render():
    f = ImageFont.truetype(TTF, 19)
    out = {}
    for ch, g in ENC.items():
        if ch == ' ':
            out[g] = ([[0] * 12 for _ in range(12)], SPACE_ADV)
            continue
        im = Image.new('1', (24, 32), 0)
        ImageDraw.Draw(im).text((0, 0), ch, font=f, fill=1)
        px = im.load()
        rows = [[1 if px[x, TOP + y] else 0 for x in range(12)] for y in range(12)]
        adv = int(round(f.getlength(ch)))
        assert adv <= 12 and not any(px[x, y] for x in range(12, 24) for y in range(32)), ch
        assert not any(px[x, y] for x in range(24) for y in list(range(0, TOP)) + list(range(TOP + 12, 32))), ch
        out[g] = (rows, adv)
    return out


def widths():
    return {g: adv for g, (rows, adv) in _render().items()}


def patch(page):
    page = bytearray(page)
    assert len(page) == 0x8000
    for g, (rows, adv) in _render().items():
        plane = g % 3
        cx = (g // 3) % 21 * 12
        cy = (g // 3) // 21 * 12
        for y in range(12):
            for x in range(12):
                X = cx + x
                o = (cy + y) * 128 + X // 2
                bit = 1 << (plane + (4 if X & 1 else 0))
                page[o] = (page[o] | bit) if rows[y][x] else (page[o] & ~bit & 0xFF)
    return bytes(page)


def encode(s):
    try:
        return [ENC[c] for c in s]
    except KeyError as e:
        raise ValueError('no glyph for %r in %r' % (e.args[0], s))


def text_width(s):
    w = widths()
    return sum(w[ENC[c]] for c in s)


if __name__ == '__main__':
    r = _render()
    chars = sorted(ENC, key=lambda c: ENC[c])
    Z = 4
    im = Image.new('RGB', (len(chars) * 13 * Z, 14 * Z), (40, 40, 40))
    for i, ch in enumerate(chars):
        rows, adv = r[ENC[ch]]
        for y in range(12):
            for x in range(12):
                col = (255, 255, 255) if rows[y][x] else ((0, 0, 0) if x < adv else (70, 0, 0))
                for dy in range(Z):
                    for dx in range(Z):
                        im.putpixel(((i * 13 + x) * Z + dx, (1 + y) * Z + dy), col)
    os.makedirs(os.path.dirname(os.path.abspath(sys.argv[2])), exist_ok=True)
    im.save(sys.argv[2])
    print(len(chars), 'glyphs; widths', sorted(set(a for _, a in r.values())))
