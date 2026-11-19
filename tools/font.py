"""Game font access: WIN.BIN entry 0, chunk at 0x1f8 (type 0x12, 4bpp 256x256, VRAM 768,0).
Bits 0..2 of each 4bpp pixel are three independent 1bpp planes; bit 3 is always set.
Glyphs are 12x12 cells, 21 per row, 21 rows per plane -> 441 cells x 3 planes = 1323 glyphs.
Glyph index g -> plane g % 3, cell g // 3."""
import struct
FONT_CHUNK = 0x1f8
FONT_DATA = FONT_CHUNK + 20
CELL = 12
PER_ROW = 21
NGLYPH = 441 * 3

def load_planes(win):
    raw = win[FONT_DATA:FONT_DATA + 128 * 256]
    px = [[0] * 256 for _ in range(256)]
    for y in range(256):
        for x in range(256):
            b = raw[y * 128 + x // 2]
            px[y][x] = (b >> 4) if x & 1 else b & 15
    return px

def glyph(px, g):
    p, c = g % 3, g // 3
    cx, cy = (c % PER_ROW) * CELL, (c // PER_ROW) * CELL
    return [[(px[cy + y][cx + x] >> p) & 1 for x in range(CELL)] for y in range(CELL)]

if __name__ == '__main__':
    import sys
    from PIL import Image
    win = open(sys.argv[1], 'rb').read()
    px = load_planes(win)
    cols = 32; rows = (NGLYPH + cols - 1) // cols
    im = Image.new('L', (cols * 13 + 1, rows * 13 + 1), 80)
    for g in range(NGLYPH):
        gl = glyph(px, g)
        for y in range(12):
            for x in range(12):
                im.putpixel((1 + (g % cols) * 13 + x, 1 + (g // cols) * 13 + y), 255 if gl[y][x] else 0)
    im.save(sys.argv[2])
