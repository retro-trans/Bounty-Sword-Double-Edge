"""Copy finished translations to untranslated rows whose Japanese text is identical.

    python tools/propagate.py --dry     report what would change (read the sample first)
    python tools/propagate.py
    python tools/propagate.py --sync    also overwrite copied rows that differ from the scene
                                        that has a draft (work/translation/en/drafts/S###.py)

Only rows of 8+ characters and the choice rows are copied: a short line can mean
different things in different scenes and must be translated in context. Rows of the
common banks (bank 'battle' / 'bank7', identical in every scene) are always copied.
"""
import collections
import glob
import json
import os
import sys

dry = '--dry' in sys.argv
files = [p for p in sorted(glob.glob('work/translation/en/scenes/S*.json')) if not p.endswith('.en.json')]
data = {p: json.load(open(p, encoding='utf-8')) for p in files}
sync = '--sync' in sys.argv
known = {}
clash = collections.Counter()
drafted = lambda p: os.path.exists('work/translation/en/drafts/%s.py' % os.path.basename(p)[:4])
for rows in [data[p] for p in sorted(data, key=lambda p: (not drafted(p), p))]:
    for r in rows:
        if r['en']:
            key = (r['kind'], r['jp'], r.get('bank', 'scene') != 'scene')
            if key in known and known[key] != r['en']:
                clash[r['jp']] += 1
            known.setdefault(key, r['en'])
n = 0
sample = []
per_file = collections.Counter()
for p, rows in data.items():
    for r in rows:
        key = (r['kind'], r['jp'], r.get('bank', 'scene') != 'scene')
        if r['en'] and not (sync and not drafted(p) and key in known and known[key] != r['en']):
            continue
        if key in known and (len(r['jp']) >= 8 or r['kind'] == 'choice' or r.get('bank', 'scene') != 'scene'):
            r['en'] = known[key]
            n += 1
            per_file[p[-9:-5]] += 1
            if len(sample) < 8:
                sample.append((r['id'], known[key]))
print('rows filled', n, dict(per_file))
print('conflicting translations of the same source:', len(clash))
for s in sample:
    print(' ', s[0], '=>', s[1][:70])
if not dry:
    for p, rows in data.items():
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
