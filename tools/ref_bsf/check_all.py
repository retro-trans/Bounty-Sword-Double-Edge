"""Check every translated scene row (the same checks as tools/apply_draft.py) and print totals.

    python tools/check_all.py [-v]

Reports: rows, translated, empty (by scene), and per-row problems: tag mismatch,
character without a glyph, line too wide, too many lines, too many glyphs.
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont

verbose = '-v' in sys.argv
W = enfont.widths()
tag = re.compile(r'\{[^}]*\}')
FW_SPACE = chr(0x3000)
JP_QUOTE = chr(0x300C)


def measure(line):
    px = 0
    vis = 0
    pos = 0
    for m in tag.finditer(line):
        seg = line[pos:m.start()]
        px += sum(W[enfont.ENC[c]] for c in seg)
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
    px += sum(W[enfont.ENC[c]] for c in seg)
    vis += sum(1 for c in seg if c != ' ')
    return px, vis


tot = collections.Counter()
empty = collections.Counter()
problems = []
for p in sorted(glob.glob('work/translation/en/scenes/S*.json')):
    if p.endswith('.en.json'):
        continue
    for r in json.load(open(p, encoding='utf-8')):
        if r['kind'] == 'data?':
            tot['data'] += 1
            continue
        tot['rows'] += 1
        t = r['en']
        if not t:
            empty[r['id'][:4]] += 1
            continue
        tot['translated'] += 1
        jt = sorted(x for x in tag.findall(r['jp']) if x != '{n}')
        et = sorted(x for x in tag.findall(t) if x != '{n}')
        if jt != et:
            problems.append((r['id'], 'TAG', '%s vs %s' % (jt, et)))
        bad = sorted(set(c for c in tag.sub('', t) if c not in enfont.ENC))
        if bad:
            problems.append((r['id'], 'GLYPH', ''.join(bad)))
            continue
        telop = r['kind'] == 'dlg' and not r['jp'].lstrip(FW_SPACE).startswith(JP_QUOTE)
        limit = 247 if telop else 240
        lines = t.split('{n}')
        vis = 0
        for ln in lines:
            px, v = measure(ln.strip(' ') if telop else ln)
            vis += v
            if px > limit:
                problems.append((r['id'], 'WIDE', '%d px: %s' % (px, ln)))
        if r['kind'] == 'dlg' and len(lines) > max(3, r['jp'].count('{n}') + 1):
            problems.append((r['id'], 'LINES', str(len(lines))))
        if vis > 110:
            problems.append((r['id'], 'GLYPHS', str(vis)))
print('rows %d, translated %d, empty %d, data rows %d' % (tot['rows'], tot['translated'], sum(empty.values()), tot['data']))
if empty:
    print('empty by scene:', ' '.join('%s:%d' % kv for kv in sorted(empty.items())))
kinds = collections.Counter(k for _, k, _ in problems)
print('problems:', dict(kinds) if problems else 'none')
for rid, k, msg in (problems if verbose else problems[:15]):
    print('  %s %s %s' % (rid, k, msg))
