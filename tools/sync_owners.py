"""Every copy row (owners.json: row -> owner row) takes its owner's current English.

    python tools/sync_owners.py [--dry]

propagate.py --sync leaves drafted scenes alone, so copies inside drafted scenes can keep text from
before a review. Owners are never changed. Drafts hold only owned rows, so re-applying a draft
does not undo this.
"""
import glob
import json
import sys

dry = '--dry' in sys.argv
own = json.load(open('work/translation/en/owners.json'))
files = [p for p in sorted(glob.glob('work/translation/en/scenes/[KS]*.json')) if not p.endswith('.en.json')]
data = {p: json.load(open(p, encoding='utf-8')) for p in files}
text = {r['id']: r['en'] for rows in data.values() for r in rows}
n = 0
sample = []
for p, rows in data.items():
    ch = False
    for r in rows:
        o = own.get(r['id'], r['id'])
        if o != r['id'] and o in text and text[o] and r['en'] != text[o]:
            if len(sample) < 12:
                sample.append((r['id'], r['en'][:50], text[o][:50]))
            r['en'] = text[o]
            n += 1
            ch = True
    if ch and not dry:
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('copy rows updated' if not dry else 'copy rows to update', n)
for s in sample:
    print(' %s | %s  ->  %s' % s)
