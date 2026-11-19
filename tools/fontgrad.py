"""Vertical gradient on the game font (two tones with a dithered blend).

The font page (4bpp, three glyph bit planes 0-2 per 12x12 cell) has bit 3 set on every pixel, and
the font CLUTs (16 entries each, one CLUT per plane: entries with the plane bit and bit 3 = the text
colour, everything else 0x8000 = draws nothing) never use the entries with bit 3 clear. So:

* page: bit 3 stays set on cell rows 0-4 (TOP_ROWS), alternates per pixel on rows 5-6 (BLEND_ROWS),
  is cleared on rows 7-11;
* CLUTs: plane bit + bit 3 -> the top shade, plane bit without bit 3 -> the bottom shade.

Font CLUT sets (three CLUTs = 0x60 bytes each, found by scanning every file for the pattern):
WIN.BIN entry 0 at +0x8084 (text 6B5A, shadow 2529, 18C6, red 001A, 1084) and entry 6 at +0x10594
(red 0012). Dark colours (shadows) keep one shade.

    page(data) -> font page bytes with the bit-3 mask
    cluts(win, offs) -> WIN.BIN bytes with the gradient CLUTs (offs: the archive's entry offsets)
    python tools/fontgrad.py preview <out.png>
"""
import struct

TOP_ROWS = 5            # rows 0-4: top shade
BLEND_ROWS = (5, 6)     # dithered
SETS = [(0, 0x8084, 5), (6, 0x10594, 1)]     # (WIN entry, offset in entry, number of 3-CLUT groups)


def rgb(c):
    return c & 31, (c >> 5) & 31, (c >> 10) & 31


def pack(r, g, b):
    return min(31, r) | min(31, g) << 5 | min(31, b) << 10


# original colour -> (top, bottom)
SHADES = {
    0x6B5A: (pack(29, 29, 29), pack(24, 24, 24)),     # text: soft white to light grey (old flat 26)
    0x001A: (pack(28, 2, 1), pack(23, 0, 0)),         # red
    0x0012: (pack(21, 1, 0), pack(16, 0, 0)),         # dark red
    0x2529: (pack(1, 1, 1), pack(1, 1, 1)),           # menu windows (colour 0x30, beige): black
    0x18C6: (pack(10, 9, 8), pack(10, 9, 8)),         # drop shadow: light warm grey (menus draw it at 2x)
}                                                    # (0 would be transparent; shadow: hooks.SHADOW_TEST)


def shades(c):
    if c in SHADES:
        return SHADES[c]
    return c, c                                      # shadows / dark tones: flat


def bit3(x, y):
    r = y % 12
    if r < TOP_ROWS:
        return True
    if r in BLEND_ROWS:
        return (x + r) % 2 == 0
    return False


def page(data):
    d = bytearray(data)
    assert len(d) == 0x8000
    for y in range(256):
        for x in range(256):
            o = y * 128 + x // 2
            bit = 0x80 if x & 1 else 0x08
            if bit3(x, y):
                d[o] |= bit
            else:
                d[o] &= ~bit & 0xFF
    return bytes(d)


def clut_group(d, o):
    """Three CLUTs (planes 0, 1, 2) at d[o]: rewrite in place."""
    base = struct.unpack_from('<16H', d, o)
    colour = base[9]
    assert base[:9] == (0x8000,) * 9 and colour != 0x8000, hex(o)
    top, bot = shades(colour)
    for p in range(3):
        e = list(struct.unpack_from('<16H', d, o + 32 * p))
        for n in range(16):
            if n & (1 << p):
                assert (n < 8 and e[n] == 0x8000) or (n >= 8 and e[n] == colour), (hex(o), p, n)
                e[n] = top if n & 8 else bot
        struct.pack_into('<16H', d, o + 32 * p, *e)


def cluts(win, offs):
    d = bytearray(win)
    for ent, off, groups in SETS:
        for g in range(groups):
            clut_group(d, offs[ent] + off + 0x60 * g)
    return bytes(d)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, __import__('os').path.dirname(__file__))
    import enfont
    from PIL import Image
    r = enfont._render()
    chars = 'Kane: "Is this the HQ, Sera?" Rheinmetall, 4199.'
    Z = 4
    top, bot = SHADES[0x6B5A]
    im = Image.new('RGB', (sum(r[enfont.ENC[c]][1] for c in chars) * Z + 8, 14 * Z), (24, 32, 120))
    x0 = 4
    for c in chars:
        rows, adv = r[enfont.ENC[c]]
        for y in range(12):
            for x in range(12):
                if rows[y][x]:
                    col = top if bit3(x0 // Z + x, y) else bot
                    rr, gg, bb = rgb(col)
                    for dy in range(Z):
                        for dx in range(Z):
                            im.putpixel((x0 + x * Z + dx, (1 + y) * Z + dy), (rr * 8, gg * 8, bb * 8))
        x0 += adv * Z
    im.save(sys.argv[2])
    print(sys.argv[2])
