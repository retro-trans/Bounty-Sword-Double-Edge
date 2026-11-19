"""Write committable copies of the translation working files without the Japanese script text.

    python tools/strip_jp.py            all work/translation/<lang>/**/*.json -> *.en.json
    python tools/strip_jp.py --dry      report only

The working files (id, off, end, block, spk, kind, jp, en) stay local (.gitignore).
The *.en.json copies keep everything except 'jp', plus a hash of the source text so a
changed source row can be detected when the copy is merged back.
"""
import glob
import hashlib
import json
import os
import sys

dry = '--dry' in sys.argv
n = 0
for p in sorted(glob.glob('work/translation/*/**/*.json', recursive=True)):
    if p.endswith('.en.json'):
        continue
    rows = json.load(open(p, encoding='utf-8'))
    if not isinstance(rows, list) or not rows or 'jp' not in rows[0]:
        continue                      # not a row file
    out = []
    for r in rows:
        o = {k: v for k, v in r.items() if k != 'jp'}
        o['src'] = hashlib.sha1(r['jp'].encode('utf-8')).hexdigest()[:12]
        out.append(o)
    done = sum(1 for r in rows if r.get('en'))
    dst = p[:-5] + '.en.json'
    print('%-50s rows %4d translated %4d' % (os.path.basename(dst), len(rows), done))
    if not dry and done:
        json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        n += 1
print('written', n)
