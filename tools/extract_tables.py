"""Extract string tables that are 'u32 offset table + strings ended by FFFF' (FFFE = new line).

    python tools/extract_tables.py          -> work/translation/en/tables/W005.json, W076.json, W077.json

WIN.BIN entries 5, 76, 77: 62 table slots each (shop / service lines). A string is
<speaker name> FFFE <text>; some entries are empty. Low glyph codes that the game
replaces at run time are written as {v:XX} (hex glyph code): seen 01, 02 (item / name)
2D (mercenary name as speaker), 2E (amount).
Row: id, index (table slot), off, jp, en.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bs2_text import CM

VARS = set()      # run-time placeholders are not identified for this game yet


def decode(ws):
    s = ''
    for w in ws:
        if w == 0xFFFE:
            s += '{n}'
        elif w in VARS:
            s += '{v:%02X}' % w
        else:
            s += CM.get(w, '{%04x}' % w)
    return s


def table(path, name):
    d = open(path, 'rb').read()
    first = min(x for x in struct.unpack_from('<62I', d, 0) if x)
    n = first // 4
    offs = struct.unpack_from('<%dI' % n, d, 0)
    rows = []
    for i, o in enumerate(offs):
        if not o:
            continue
        ws = []
        q = o
        while True:
            w = struct.unpack_from('<H', d, q)[0]
            q += 2
            if w == 0xFFFF:
                break
            ws.append(w)
        rows.append(dict(id='%s_%03d' % (name, i), index=i, off=o, jp=decode(ws), en=''))
    return rows


if __name__ == '__main__':
    out = 'work/translation/en/tables'
    os.makedirs(out, exist_ok=True)
    for idx in (5, 76, 77):
        name = 'W%03d' % idx
        rows = table('work/source/win/%03d.bin' % idx, name)
        dst = os.path.join(out, name + '.json')
        if os.path.exists(dst):
            old = {r['id']: r for r in json.load(open(dst, encoding='utf-8'))}
            for r in rows:
                if r['id'] in old and old[r['id']]['jp'] == r['jp']:
                    r['en'] = old[r['id']]['en']
        json.dump(rows, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(name, 'rows', len(rows), 'non-empty', sum(1 for r in rows if r['jp']), 'chars', sum(len(r['jp']) for r in rows),
              'unique', len(set(r['jp'] for r in rows if r['jp'])))
