"""List real UI strings (u16 glyph runs ended by FFFF, FFFE = new line) in the EXE, overlays and
WIN.BIN entries. Writes work/source/dump/ui_strings.txt (contains Japanese: never commit).

A run counts as text when it has at least 2 kana or kanji glyphs and 2+ glyphs, ends at FFFF, and
at most a quarter of its glyphs are rare kanji (code noise)."""
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bs2_text as T


def strings(d):
    n = len(d) // 2
    ws = struct.unpack_from('<%dH' % n, d)
    out = []
    i = 0
    while i < n:
        j = i
        kana = g = 0
        while j < n and (ws[j] < T.NGLYPH or ws[j] in (0xFFFE, 0xFFFC, 0xFFFD) or 0xC000 <= ws[j] < 0xC200):
            if 0xC000 <= ws[j] < 0xC200:      # window control code + one argument word
                j += 2
                continue
            if 81 <= ws[j] < T.NGLYPH:      # kana and kanji (all-kanji menu words like 地 図 count)
                kana += 1
            if 0 < ws[j] < T.NGLYPH:
                g += 1
            j += 1
        j = min(j, n)
        if j < n and ws[j] == 0xFFFF and kana >= 2 and g >= 2:
            out.append((i * 2, ws[i:j]))
            i = j + 1
        else:
            i = max(j, i + 1)
    return out


def show(ws):
    return ''.join({0xFFFE: '/', 0xFFFC: '<', 0xFFFD: '>'}.get(w, T.CM.get(w, '?') if w else ' ') for w in ws)


if __name__ == '__main__':
    files = [('exe', 'work/source/disc/SLPS_014.79')] + \
        [('ovl%s' % os.path.basename(p)[:3], p) for p in sorted(glob.glob('work/source/ovl/*.bin'))] + \
        [('win%s' % os.path.basename(p)[:3], p) for p in sorted(glob.glob('work/source/win/*.bin')) if os.path.getsize(p) < 0x20000]
    tot = 0
    with open('work/source/dump/ui_strings.txt', 'w', encoding='utf-8') as f:
        for nm, p in files:
            d = open(p, 'rb').read()
            if nm == 'exe':
                d = d[0x800:]
            ss = strings(d)
            if not ss:
                continue
            g = sum(sum(1 for w in ws if 0 < w < T.NGLYPH) for _, ws in ss)
            tot += g
            print('%-8s strings %4d glyphs %6d' % (nm, len(ss), g))
            for o, ws in ss:
                f.write('%s %06x %s\n' % (nm, o, show(ws)))
    print('total glyphs', tot)
