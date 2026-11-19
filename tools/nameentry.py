"""Name-entry screen (overlay 20): Latin letters first, English default names, English menu row.

The grid is a set of pages (u16 glyph strings, rows of 10 glyphs ended by FFFE, page ended by FFFF);
the first row of each page is the menu row 'すすむ もどる 決定' (cursor right / back / confirm).
The game already has a page with digits, A-Z and a-z (third page); those cells are drawn by the
English font, so that page's letter rows are swapped with the hiragana page's rows (the hiragana page
is the one shown first). The second copy of the hiragana page (another entry screen) gets the Latin
rows too, and the third copy (the table the typed character is read from) is swapped like the first. Default names ケーン / セラ (8-glyph slots) become Kane / Sera.

    patches() -> {overlay 20 file offset: bytes}, each checked against the original
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont
import bs2_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVL20 = os.path.join(ROOT, 'work', 'source', 'ovl', '020.bin')
ROW = 22                       # 10 glyphs + FFFE
ROWS = 9
HIRA_ROWS = 0x29F28            # first letter row of the hiragana page (after its menu row)
HIRA2_ROWS = 0x2A642           # second copy (another entry screen)
LATIN_ROWS = 0x2A0E4           # first letter row of the digits/Latin page
HIRA3_ROWS = 0x345C2           # third copy: the table the game reads the typed character from
LATIN3_ROWS = 0x3477E
DEFAULTS = {0x2A48A: 'Kane', 0x2A49A: 'Sera'}   # 8-glyph slots
MENU_EN = 'Fwd Bck OK'         # same cell positions as すすむ_もどる_決定


def glyphs(s):
    return [0 if c == ' ' else enfont.ENC[c] for c in s]


def fixed(b):
    """Displayed grid copies: every glyph as FIXED_BASE + glyph, so the menu hook draws it at the
    fixed 12-px cell (the cursor moves by cells). The typed-character table keeps plain codes."""
    from hooks import FIXED_BASE
    ws = struct.unpack('<%dH' % (len(b) // 2), b)
    return struct.pack('<%dH' % len(ws), *[w + FIXED_BASE if 0 < w < 0x8000 else w for w in ws])


TYPED = (0x34500, 0x34B00)    # the typed-character table (all its pages and menu rows): plain codes


def patches():
    d = open(OVL20, 'rb').read()
    inv = {v: k for k, v in bs2_text.CM.items()}
    out = {}
    hira = d[HIRA_ROWS:HIRA_ROWS + ROW * ROWS]
    latin = d[LATIN_ROWS:LATIN_ROWS + ROW * ROWS]
    assert struct.unpack_from('<H', hira, 0)[0] == inv['あ'] and struct.unpack_from('<H', latin, 0)[0] == inv['０']
    for r in range(ROWS):
        assert struct.unpack_from('<H', hira, r * ROW + 20)[0] == 0xFFFE
        assert struct.unpack_from('<H', latin, r * ROW + 20)[0] == 0xFFFE
    out[HIRA_ROWS] = (hira, fixed(latin))
    out[LATIN_ROWS] = (latin, fixed(hira))
    out[HIRA2_ROWS] = (d[HIRA2_ROWS:HIRA2_ROWS + ROW * ROWS], fixed(latin))
    assert d[HIRA2_ROWS:HIRA2_ROWS + ROW * ROWS] == hira
    hira3 = d[HIRA3_ROWS:HIRA3_ROWS + ROW * ROWS]
    latin3 = d[LATIN3_ROWS:LATIN3_ROWS + ROW * ROWS]
    assert hira3 == hira and latin3 == latin
    out[HIRA3_ROWS] = (hira3, latin3)
    out[LATIN3_ROWS] = (latin3, hira3)
    menu_jp = struct.pack('<10H', *[inv[c] if c != '_' else 0 for c in 'すすむ_もどる_決定'])
    menu_en = struct.pack('<10H', *glyphs(MENU_EN))
    o = d.find(menu_jp)
    while o >= 0:
        if o % 2 == 0:
            out[o] = (menu_jp, menu_en if TYPED[0] <= o < TYPED[1] else fixed(menu_en))
        o = d.find(menu_jp, o + 2)
    for o, name in DEFAULTS.items():
        old = d[o:o + 16]
        new = struct.pack('<8H', *(glyphs(name) + [0] * (8 - len(name))))
        out[o] = (old, new)
    return out


if __name__ == '__main__':
    for o, (old, new) in sorted(patches().items()):
        print('%06x %3d bytes' % (o, len(new)))


# ---------------------------------------------------------------- opening telegram (overlay 20)
OVL20_LOAD = 0x8011888C
TELE_JAL_BC = 0x80121290       # jal 0x80019268, pen at 0x801667BC
TELE_JAL_B4 = 0x801210A4       # jal 0x80019268, pen at 0x801667B4
TELE_PTR = 0x8012CF40          # lui v0, 0x8015 / (cf44) / addiu v0, v0, -0x7968 -> 0x80148698
TELE_NEW = 0x80167000          # zero in the file and in RAM while the telegram shows
HERO = 0xF3                    # the printer replaces this glyph with the first hero's name
# The printer keeps a 200-entry glyph buffer per page (cleared by FFFD, 0x80121488), so every page
# stays under PAGE_MAX glyphs (spaces count; the hero tag counts as 8). Page break: FFFC (wait for a
# button) FFFD (clear) FFFE, as in the original prologue.
PAGE_MAX = 190
TELEGRAM = [
    ['"From: Romulus Army,',
     ' Special Service Agency HQ',
     ' To: Special Service 2nd Lt. #"',
     '"Re: personnel replacements. Approved."'],
    ['"Stand by in Ship Town, in the',
     ' demilitarized zone, and await contact',
     ' from Special Service Captain Ixion."',
     '"Postscript"'],
    ['"Rheinmetall soldiers have landed',
     ' in large numbers."',
     '"Make haste in carrying out',
     ' your mission."',
     '"End of message"'],
]
# The war prologue follows the telegram's FFFF directly (0x2FF02, no reference of its own: the
# printer reads on past the telegram), so it goes right after the English telegram. The original
# starts with FFFE FFFE and puts FFFE x4 before its last line.
PROLOGUE = [
    ['"September 1, Divine Calendar 4199"',
     '"The conflict over the Steel Island',
     ' spread across all of North Europea."'],
    ['"On this day, the United Republican Kingdom',
     ' of Rheinmetall declared war on the',
     ' Holy Nation of Assyria to the south."'],
    ['"At almost the same time, in the Republic',
     ' of Romulus, soldiers bent on restoring the',
     ' monarchy staged a coup and seized power."'],
    ['"These events became the trigger: the',
     ' Rheinmetall-Folgore coalition and the',
     ' Romulus-Assyria alliance were formed."'],
    ['"All of North Europea was to be swallowed',
     ' by the flames of war."'],
    ['', '', '', '"Thus began the Third Great Europea War."'],
]
BREAK = [0xFFFC, 0xFFFD, 0xFFFE]


def _line(line):
    assert enfont.text_width(line.replace('#', 'MMMMMM')) <= 250, line
    return [HERO if c == '#' else enfont.ENC[c] for c in line]


def _pages(pages):
    ws = []
    for p, page in enumerate(pages):
        assert sum(len(l.replace('#', '########')) for l in page) <= PAGE_MAX, page
        if p:
            ws += BREAK
        for i, line in enumerate(page):
            if i:
                ws.append(0xFFFE)
            ws += _line(line)
    return ws


def telegram_blob():
    ws = _pages(TELEGRAM) + [0xFFFF, 0xFFFE, 0xFFFE] + _pages(PROLOGUE) + [0xFFFF]
    return struct.pack('<%dH' % len(ws), *ws)


def telegram_patches(sym):
    """-> {overlay 20 file offset: (old bytes, new bytes)}"""
    from masm import assemble
    d = open(OVL20, 'rb').read()
    out = {}
    jal_add = struct.pack('<I', 0x0C000000 | ((0x80019268 >> 2) & 0x3FFFFFF))
    for site, hook in ((TELE_JAL_BC, 'tele_bc'), (TELE_JAL_B4, 'tele_b4')):
        o = site - OVL20_LOAD
        assert d[o:o + 4] == jal_add, hex(site)
        out[o] = (jal_add, struct.pack('<I', 0x0C000000 | ((sym[hook] >> 2) & 0x3FFFFFF)))
    o = TELE_PTR - OVL20_LOAD
    old = d[o:o + 12]
    assert struct.unpack_from('<3I', old) == (0x3C028015, struct.unpack_from('<I', old, 4)[0], 0x24428698), old.hex()
    new = struct.pack('<I', 0x3C020000 | ((TELE_NEW + 0x8000) >> 16)) + old[4:8] + \
        struct.pack('<I', 0x24420000 | (TELE_NEW & 0xFFFF))
    assert TELE_NEW & 0x8000 == 0
    out[o] = (old, new)
    blob = telegram_blob()
    o = TELE_NEW - OVL20_LOAD
    assert not any(d[o:o + len(blob) + 16])
    out[o] = (bytes(len(blob)), blob)
    return out


# ---------------------------------------------------------------- map day counter (overlay 20)
# 第 / 日 are two one-glyph strings (第 FFFF 日 FFFF at 0x30690, read through separate pointers to
# 0x30690 and 0x30694) printed around the day number. English: 第 -> "Day " in two pair cells
# ending at 0x30694, so the 日 pointer lands on an end marker and prints nothing ("Day 1").
DAY_OFF = 0x30690


def day_patches():
    from hooks import pack_pairs
    d = open(OVL20, 'rb').read()
    inv = {v: k for k, v in bs2_text.CM.items()}
    old = d[DAY_OFF:DAY_OFF + 8]
    assert struct.unpack('<4H', old) == (inv['第'], 0xFFFF, inv['日'], 0xFFFF), old.hex()
    toks = pack_pairs([enfont.ENC[c] for c in 'Day '])
    assert len(toks) == 2
    return {DAY_OFF: (old, struct.pack('<4H', toks[0], toks[1], 0xFFFF, 0xFFFF))}
