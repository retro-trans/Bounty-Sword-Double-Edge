"""Copy finished translations to untranslated rows whose Japanese text is identical.

    python tools/propagate.py --dry     report what would change (read the sample first)
    python tools/propagate.py
    python tools/propagate.py --sync    also overwrite copied rows that differ from the scene
                                        that has a draft (work/translation/en/drafts/S###.py)

Which rows share a translation is decided by tools/rowkeys.py (short lines only match a copy
with the same speaker and the same neighbouring rows). Rows of the
common banks (bank 'battle' / 'bank7' / 'orphan', repeated in many files) are always copied.
"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

dry = '--dry' in sys.argv
files = [p for p in sorted(glob.glob('work/translation/en/scenes/[KS]*.json')) if not p.endswith('.en.json')]
import rowkeys
data = {p: json.load(open(p, encoding='utf-8')) for p in files}
keys = {p: rowkeys.keys_for(rows) for p, rows in data.items()}
sync = '--sync' in sys.argv
unify = '--unify' in sys.argv      # every copy takes the text of the first scene in order, drafted or not
known = {}
clash = collections.Counter()
drafted = lambda p: os.path.exists('work/translation/en/drafts/%s.py' % os.path.basename(p)[:4])
order = sorted(data, key=lambda p: ((not drafted(p)) and not unify, os.path.basename(p)[0] != 'K', p))
for p in order:
    for r, key in zip(data[p], keys[p]):
        if r['en']:
            if key in known and known[key] != r['en']:
                clash[r['id']] += 1
            known.setdefault(key, r['en'])
n = 0
sample = []
per_file = collections.Counter()
for p, rows in data.items():
    for r, key in zip(rows, keys[p]):
        if r['en'] and not (key in known and known[key] != r['en'] and (unify or (sync and not drafted(p)))):
            continue
        if key in known:
            r['en'] = known[key]
            n += 1
            per_file[os.path.basename(p)[:4]] += 1
            if len(sample) < 8:
                sample.append((r['id'], known[key]))
print('rows filled', n, 'in', len(per_file), 'files')
print('conflicting translations of the same source:', len(clash), list(clash)[:10])
for s in sample:
    print(' ', s[0], '=>', s[1][:70])
if not dry:
    for p, rows in data.items():
        if per_file[os.path.basename(p)[:4]]:
            json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
