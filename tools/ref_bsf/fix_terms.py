"""Unify spellings that different translators coined for the same term.

    python tools/fix_terms.py --dry     counts and samples (read them before applying)
    python tools/fix_terms.py

Works on the English only: the `en` field of every scene/table file and the same strings in
work/translation/en/drafts/*.py (so re-applying a draft does not bring an old spelling back).
Run it AFTER translators' fixes, never while a translator is still writing (BASE_RULES:
agents fix meaning, scripts fix names). After applying, run tools/check_all.py: a
replacement can make a line wider.
"""
import glob
import json
import re
import sys

dry = '--dry' in sys.argv

# (pattern, replacement) -- whole phrases, case-sensitive
FIX = [
    (r'\bChebourg\b', 'Cherbourg'),
    (r'\bSealed Tomb\b', 'Sealed Crypt'),
    (r'\bPrimeval Isle\b', 'Ancient Isle'),
    (r"\bSage's Village\b", 'Hamlet of the Sages'),
    (r'\bDemon General\b', 'Sorcerer General'),
    (r'\bGoddess Unit\b', 'Goddess Corps'),
    (r'\bFour Mightiest Generals\b', 'Four Great Generals'),
    (r'\bfour greatest generals\b', 'Four Great Generals'),
    (r'\b17th Independent Knights of Rheinmetall\b', '17th Independent Knights'),
    (r'\b17th Independent Knight Corps\b', '17th Independent Knights'),
    (r'\bsword of reward\b', 'Bounty Sword'),
    (r'\bheavenly qi\b', 'heavenly ki'),
]

files = [p for p in sorted(glob.glob('work/translation/en/scenes/S*.json') + glob.glob('work/translation/en/tables/*.json'))
         if not p.endswith('.en.json')]
total = {pat: 0 for pat, _ in FIX}
samples = {pat: [] for pat, _ in FIX}
changed_rows = []
for p in files:
    rows = json.load(open(p, encoding='utf-8'))
    dirty = False
    for r in rows:
        t = r.get('en') or ''
        new = t
        for pat, rep in FIX:
            new2, n = re.subn(pat, rep, new)
            if n:
                total[pat] += n
                if len(samples[pat]) < 3:
                    samples[pat].append((r['id'], new2[:70]))
            new = new2
        if new != t:
            r['en'] = new
            dirty = True
            changed_rows.append(r['id'])
    if dirty and not dry:
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
drafts = 0
for p in sorted(glob.glob('work/translation/en/drafts/*.py')):
    s = open(p, encoding='utf-8').read()
    new = s
    for pat, rep in FIX:
        new = re.sub(pat, rep, new)
    if new != s:
        drafts += 1
        if not dry:
            open(p, 'w', encoding='utf-8').write(new)
for pat, rep in FIX:
    print('%4d  %s -> %s' % (total[pat], pat.replace(r'\b', ''), rep))
    for rid, t in samples[pat]:
        print('        %s  %s' % (rid, t))
print('rows changed', len(changed_rows), '| draft files changed', drafts, '| dry run' if dry else '| applied')
