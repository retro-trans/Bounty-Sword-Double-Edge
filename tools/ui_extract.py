"""Extract UI / system strings for translation (in-place insertion with letter pairs).

    python tools/ui_extract.py        -> work/translation/en/ui/<file>.json (Japanese: never commit)

Sources: the EXE (item database, system text), overlays 1, 2, 20 and the small ones, WIN.BIN
string tables 5, 76, 77. A string is a run of u16 glyph codes ended by FFFF (tools/ui_scan.py rules).
It is split into lines at FFFE / FFFC / FFFD and at control words (>= 0x8000; a window control code
C000-C1FF is followed by one argument word, which is never part of a line);
each line is one row:
    id, file, off (byte offset in the source file of the line's first word), slots (u16 words the
    line occupies), raw_prefix (leading words kept as they are: window-template parameters),
    jp, en
English is inserted in the same slots: letter pairs (two letters per word, expanded by the menu
hook in tools/hooks.py build_exe) and padded with 0 (blank). So a row holds 2 * slots letters,
minus one word per glyph that cannot pair. tools/ui_insert.py checks and writes.

Window-template parameters: in the overlays, a string right after FFFF that starts with 3+ codes
below 81 (punctuation / digits / Latin cells) followed by kana or kanji keeps those leading codes raw.
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bs2_text as T
from ui_scan import strings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'ui')
BREAKS = (0xFFFE, 0xFFFC, 0xFFFD)


def sources():
    s = [('EXE', os.path.join(ROOT, 'work/source/disc/SLPS_014.79'), 0x800)]
    for p in sorted(glob.glob(os.path.join(ROOT, 'work/source/ovl/*.bin'))):
        s.append(('O%s' % os.path.basename(p)[:3], p, 0))
    for n in (5, 76, 77):
        s.append(('W%03d' % n, os.path.join(ROOT, 'work/source/win/%03d.bin' % n), 0))
    return s


def is_text(c):
    return 81 <= c < T.NGLYPH


def rows_of(name, path, skip):
    d = open(path, 'rb').read()
    body = d[skip:]
    rows = []
    for off, ws in strings(body):
        ws = list(ws)
        i = 0
        prefix = 0
        if name[0] == 'O':
            k = 0
            while k < len(ws) and ws[k] < 81 and ws[k] not in BREAKS:
                k += 1
            if k >= 3 and k < len(ws) and is_text(ws[k]):
                prefix = k
        start = 0
        cur = []
        pos = 0
        # control-code arguments; a "argument" that is a kana / kanji glyph is really the first letter
        # of the text (codes like C0AF / C067 / C00A insert a name or colour and take no argument)
        argpos = set(k + 1 for k, x in enumerate(ws) if 0xC000 <= x < 0xC200 and k + 1 < len(ws)
                     and not is_text(ws[k + 1]))
        for j, w in enumerate(ws + [0xFFFF]):
            if w in BREAKS or w >= 0x8000 or j in argpos:
                if cur:
                    line_off = off + 2 * start
                    rp = prefix if start == 0 else 0
                    words = cur
                    jp = ''.join(T.CM.get(x, '?') if x else ' ' for x in words[rp:])
                    if any(is_text(x) for x in words[rp:]):
                        rows.append(dict(id='%s_%06x' % (name, line_off + skip), file=name, off=line_off + skip,
                                         slots=len(words) - rp, raw_prefix=rp, jp=jp, en=''))
                cur = []
                start = j + 1
                continue
            cur.append(w)
    if name == 'EXE':
        rows = split_items(rows)
    rows += fixed_rows(name, body)
    return sorted(rows, key=lambda r: r['off'])


# Fixed-width name fields that are not FFFF-terminated strings: overlay 1 unit records (stride 0xB8,
# 8-cell name; records 0-22 = the 17 characters and the Void units). Copied into the party when a
# unit joins, so a save made before this keeps the old names for units already in it.
FIXED = {'O001': [(0xF580 + k * 0xB8, 8, 'unit_name') for k in range(23)]}


def fixed_rows(name, d):
    out = []
    for off, slots, kind in FIXED.get(name, ()):
        ws = struct.unpack_from('<%dH' % slots, d, off)
        assert all(w < T.NGLYPH for w in ws), (name, hex(off))
        jp = ''.join(T.CM.get(x, '?') if x else ' ' for x in ws)
        out.append(dict(id='%s_%06x' % (name, off), file=name, off=off, slots=slots, raw_prefix=0, jp=jp,
                        en='', kind=kind))
    return out


def split_items(rows):
    """EXE item database: 25-word text = name (10 words) + help text (15 words), one row each."""
    out = []
    for r in rows:
        if r['slots'] == 25:
            name, desc = r['jp'][:10], r['jp'][10:]
            out.append(dict(r, id='%s_%06x' % (r['file'], r['off']), slots=10, jp=name, kind='item_name'))
            out.append(dict(r, id='%s_%06x' % (r['file'], r['off'] + 20), off=r['off'] + 20, slots=15, jp=desc,
                            kind='item_help'))
        else:
            out.append(r)
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    tot = 0
    for name, path, skip in sources():
        rows = rows_of(name, path, skip)
        if not rows:
            continue
        dst = os.path.join(OUT, name + '.json')
        if os.path.exists(dst):
            old = {r['id']: r for r in json.load(open(dst, encoding='utf-8'))}
            for r in rows:
                if r['id'] in old and old[r['id']]['jp'] == r['jp']:
                    r['en'] = old[r['id']].get('en', '')
        json.dump(rows, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('%-5s rows %4d slots %5d' % (name, len(rows), sum(r['slots'] for r in rows)))
        tot += len(rows)
    print('total rows', tot)
