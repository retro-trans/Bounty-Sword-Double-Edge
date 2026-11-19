"""Check every translated scene row with the same rules as tools/apply_draft.py.

    python tools/check_all.py            summary + the first problems per kind
    python tools/check_all.py --list     every problem (to work/source/dump/check_all.txt)

Checks: tags other than {n} equal to the source; every character in the English font; line width
<= 236 px; lines per page <= max(3, source lines); <= 150 visible glyphs; no line break in a choice;
the row encodes with the relinker's encoder.
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont
import relink

W = enfont.widths()
TAG = re.compile(r'\{[^}]*\}')


def measure(line):
    px = vis = 0
    pos = 0
    for m in TAG.finditer(line):
        seg = line[pos:m.start()]
        px += sum(W[enfont.ENC[c]] for c in seg if c in enfont.ENC)
        vis += sum(1 for c in seg if c != ' ')
        t = m.group(0)[1:-1]
        if t.startswith(('hero:', 'name:')):
            k = int(t.split(':')[1])
            px += 12 * k
            vis += k
        elif t.startswith('num:'):
            px += 36
            vis += 6
        elif t == 'var':
            px += 72
            vis += 6
        pos = m.end()
    seg = line[pos:]
    px += sum(W[enfont.ENC[c]] for c in seg if c in enfont.ENC)
    vis += sum(1 for c in seg if c != ' ')
    return px, vis


def check_row(r):
    out = []
    t = r['en']
    jt = sorted(x for x in TAG.findall(r['jp']) if x != '{n}')
    et = sorted(x for x in TAG.findall(t) if x != '{n}')
    if jt != et:
        out.append(('TAG', '%s vs %s' % (jt, et)))
    bad = sorted(set(c for c in TAG.sub('', t) if c not in enfont.ENC))
    if bad:
        out.append(('GLYPH', repr(''.join(bad))))
        return out
    lines = t.split('{n}')
    vis = 0
    for ln in lines:
        px, v = measure(ln)
        vis += v
        if px > 236:
            out.append(('WIDE', '%d px: %s' % (px, ln)))
    if r['kind'] == 'dlg' and len(lines) > max(3, r['jp'].count('{n}') + 1):
        out.append(('LINES', str(len(lines))))
    if r['kind'] == 'choice' and '{n}' in t:
        out.append(('CHOICE_BREAK', t))
    if vis > relink.MAX_GLYPHS:
        out.append(('GLYPHS', str(vis)))
    try:
        relink.encode_row(t, pack=False)
    except ValueError as e:
        out.append(('ENCODE', str(e)))
    return out


if __name__ == '__main__':
    probs = []
    n = 0
    for p in sorted(glob.glob('work/translation/en/scenes/[KS]???.json')):
        for r in json.load(open(p, encoding='utf-8')):
            if not r['en']:
                probs.append((r['id'], 'EMPTY', ''))
                continue
            n += 1
            for kind, msg in check_row(r):
                probs.append((r['id'], kind, msg))
    c = collections.Counter(k for _, k, _ in probs)
    print('rows checked', n, 'problems', len(probs), dict(c))
    shown = collections.Counter()
    for rid, k, m in probs:
        if shown[k] < 6:
            print(' ', rid, k, m[:110])
            shown[k] += 1
    if '--list' in sys.argv:
        os.makedirs('work/source/dump', exist_ok=True)
        with open('work/source/dump/check_all.txt', 'w', encoding='utf-8') as f:
            for rid, k, m in probs:
                f.write('%s %s %s\n' % (rid, k, m))
