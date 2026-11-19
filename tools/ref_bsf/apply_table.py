"""Apply a table draft (work/translation/en/drafts/<name>.py, dict EN: table slot -> text)
to work/translation/en/tables/<name>.json.

    apply_table.py W005 [--dry]

Rows with the same source string as a drafted row get the same English.
Checks: {v:XX} tags must match the source; every character must be in the English font;
each line at most 240 px ({v:..} counted as 72 px); no more lines than the source has.
"""
import json
import os
import re
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont

name = sys.argv[1]
dry = '--dry' in sys.argv
EN = runpy.run_path('work/translation/en/drafts/%s.py' % name)['EN']
p = 'work/translation/en/tables/%s.json' % name
rows = json.load(open(p, encoding='utf-8'))
W = enfont.widths()
tag = re.compile(r'\{[^}]*\}')
by_index = {r['index']: r for r in rows}
problems = 0
by_jp = {}
for i, t in sorted(EN.items()):
    r = by_index.get(i)
    if r is None:
        print('NO SUCH SLOT', i)
        problems += 1
        continue
    jt = sorted(x for x in tag.findall(r['jp']) if x != '{n}')
    et = sorted(x for x in tag.findall(t) if x != '{n}')
    if jt != et:
        print('TAG MISMATCH', r['id'], jt, et)
        problems += 1
    bad = sorted(set(c for c in tag.sub('', t) if c not in enfont.ENC))
    if bad:
        print('NO GLYPH for %r' % ''.join(bad), r['id'])
        problems += 1
        continue
    lines = t.split('{n}')
    for ln in lines:
        px = sum(W[enfont.ENC[c]] for c in tag.sub('', ln)) + 72 * len(tag.findall(ln))
        if px > 240:
            print('WIDE %d px' % px, r['id'], ln)
            problems += 1
    if len(lines) > r['jp'].count('{n}') + 1:
        print('LINES %d (source %d)' % (len(lines), r['jp'].count('{n}') + 1), r['id'])
        problems += 1
    by_jp[r['jp']] = t
n = 0
for r in rows:
    if r['jp'] in by_jp:
        r['en'] = by_jp[r['jp']]
        n += 1
left = [r['id'] for r in rows if r['jp'] and not r['en']]
print('%s: rows %d, filled %d, problems %d, still empty %d %s' % (name, len(rows), n, problems, len(left), left[:10]))
if dry:
    pass
elif problems:
    print('NOT applied')
else:
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('applied')
