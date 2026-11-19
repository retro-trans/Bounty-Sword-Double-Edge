"""UI strings: apply translator drafts and patch the files in place.

    python tools/ui_insert.py apply O020 [--dry]   draft work/translation/en/ui_drafts/O020.py (EN = {row id: text})
                                                   -> checked, written into work/translation/en/ui/O020.json
    python tools/ui_insert.py check                every row of every file
    patch(name, data) -> bytes                     used by tools/build.py

Encoding: letter pairs (token 0x1000 + a*128 + b, expanded by the menu hook in tools/hooks.py
build_exe; digits are never paired, they can be run-time placeholders), then padded with 0 (blank) to the row's slots. A row holds at most 2 * slots letters
(each glyph that cannot pair costs a whole slot). A row whose English is '-' is marked as not text
and is never written. Allowed characters: those of tools/enfont.py (A-Z a-z 0-9 space ! ? : ( ) / &
% + - = ~ , . ' " ;).
"""
import json
import os
import runpy
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont
from hooks import pack_pairs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, 'work', 'translation', 'en', 'ui')
DRAFTS = os.path.join(ROOT, 'work', 'translation', 'en', 'ui_drafts')
SKIP = '-'


DIGITS = set(range(19, 29))      # full-width digit cells: the shop tables use them as run-time placeholders


TAGS = {'{hero}': 0xF3, '{name}': 0xFB}   # overlay 20 narration: first / second hero's name inserted by the game


def codes_of(text):
    out = []
    i = 0
    while i < len(text):
        for t, c in TAGS.items():
            if text.startswith(t, i):
                out.append(-c)              # negative: a tag code, never paired
                i += len(t)
                break
        else:
            out.append(enfont.ENC[text[i]])
            i += 1
    return out


# overlay 20 narration (epilogues 0x30698-0x317EE, area texts 0x467E6-0x46BF6): drawn by the
# telegram printers (tools/hooks.py TELE_SRC), which only substitute the name tags; digits pair there.
PAIR_DIGITS = {'O020': ((0x30698, 0x317EE), (0x467E6, 0x46BF6))}


def pairs_digits(r):
    return any(a <= r['off'] < b for a, b in PAIR_DIGITS.get(r['file'], ()))


def encode(text, slots, pair_digits=False):
    """Pairs, except that a digit is never paired (it may be a placeholder the game looks for),
    and the name tags {hero} / {name} become their single glyph."""
    codes = codes_of(text)
    toks = []
    run = []
    for c in codes + [None]:
        if c is None or (c in DIGITS and not pair_digits) or c < 0:
            toks += pack_pairs(run)
            run = []
            if c is not None:
                toks.append(abs(c))
        else:
            run.append(c)
    if len(toks) > slots:
        raise ValueError('needs %d slots, has %d' % (len(toks), slots))
    return toks + [0] * (slots - len(toks))


def problems(r, text):
    if text == SKIP:
        return []
    plain = text
    for t in TAGS:
        plain = plain.replace(t, '')
    bad = sorted(set(c for c in plain if c not in enfont.ENC))
    if bad:
        return ['NO GLYPH %r' % ''.join(bad)]
    try:
        encode(text, r['slots'], pairs_digits(r))
    except ValueError as e:
        return ['TOO LONG (%s; max about %d letters)' % (e, 2 * r['slots'])]
    return []


OVERRIDES = os.path.join(UI, 'overrides.json')


def load(name):
    """Rows of one file, with work/translation/en/ui/overrides.json applied:
    {"<row id>": {"skip": n}} keeps n more leading words raw (layout headers, stage codes) and
    shortens the row by n."""
    rows = json.load(open(os.path.join(UI, name + '.json'), encoding='utf-8'))
    ov = json.load(open(OVERRIDES, encoding='utf-8')) if os.path.exists(OVERRIDES) else {}
    for r in rows:
        k = ov.get(r['id'], {}).get('skip', 0)
        if k:
            r['raw_prefix'] += k
            r['slots'] -= k
    return rows


def save(name, rows):
    """Write rows back without the override adjustments."""
    ov = json.load(open(OVERRIDES, encoding='utf-8')) if os.path.exists(OVERRIDES) else {}
    out = []
    for r in rows:
        k = ov.get(r['id'], {}).get('skip', 0)
        out.append(dict(r, raw_prefix=r['raw_prefix'] - k, slots=r['slots'] + k) if k else r)
    json.dump(out, open(os.path.join(UI, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def apply(name, dry):
    rows = load(name)
    by = {r['id']: r for r in rows}
    EN = runpy.run_path(os.path.join(DRAFTS, name + '.py'))['EN']
    n = bad = 0
    for rid, text in EN.items():
        if rid not in by:
            print('NO SUCH ROW', rid)
            bad += 1
            continue
        for p in problems(by[rid], text):
            print(p, rid, text)
            bad += 1
        by[rid]['en'] = text
        n += 1
    left = [r['id'] for r in rows if not r['en']]
    print('%s: rows %d, in draft %d, problems %d, still empty %d %s' % (name, len(rows), n, bad, len(left), left[:6]))
    if not dry and not bad:
        save(name, rows)
        print('applied')
    elif not dry:
        print('NOT applied: fix the problems first')


def patch(name, data, exclude=()):
    """data: the source file's bytes -> (patched bytes, rows written). Rows keep their raw prefix
    words. exclude: (start, end) byte ranges other patches own; rows touching them are skipped."""
    if not os.path.exists(os.path.join(UI, name + '.json')):
        return data, 0
    d = bytearray(data)
    n = 0
    for r in load(name):
        if not r['en'] or r['en'] == SKIP:
            continue
        o = r['off'] + 2 * r['raw_prefix']
        if any(a < o + 2 * r['slots'] and o < b for a, b in exclude):
            continue
        old = struct.unpack_from('<%dH' % r['slots'], d, o)
        assert all(w < 0x8000 for w in old), r['id']
        struct.pack_into('<%dH' % r['slots'], d, o, *encode(r['en'], r['slots'], pairs_digits(r)))
        n += 1
    return bytes(d), n


if __name__ == '__main__':
    if sys.argv[1] == 'apply':
        apply(sys.argv[2], '--dry' in sys.argv)
    elif sys.argv[1] == 'check':
        import glob
        tot = probs = 0
        for p in sorted(glob.glob(os.path.join(UI, '*.json'))):
            if os.path.basename(p) == 'overrides.json' or p.endswith('.en.json'):
                continue
            for r in load(os.path.basename(p)[:-5]):
                if r['en']:
                    tot += 1
                    for x in problems(r, r['en']):
                        print(r['id'], x)
                        probs += 1
        print('translated rows', tot, 'problems', probs)
