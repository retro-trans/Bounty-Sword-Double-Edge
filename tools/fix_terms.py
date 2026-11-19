"""Unify spellings that different translators coined for the same term (BASE_RULES: scripts fix names).

    python tools/fix_terms.py --dry     counts and samples (read them before applying)
    python tools/fix_terms.py

Works on the English only: the `en` field of every scene file and the same strings in
work/translation/en/drafts/*.py (so re-applying a draft does not bring an old spelling back).
Run it AFTER the translators are done, never while one is still writing. Afterwards run
tools/check_all.py: a replacement can make a line wider.
"""
import glob
import json
import re
import sys

dry = '--dry' in sys.argv

# (pattern, replacement), case-sensitive; canonical forms are in work/glossary/terms.json
FIX = [
    (r'\bTreasure of Omnipotence\b', 'Almighty Treasure'),
    (r'\bIsland of Blessing\b', 'Blessed Isle'),
    (r"\bAvalon's Island of Steel\b", 'Steel Island of Avalon'),
    (r'\bEsper Girl Squad\b', 'Esper Girl Corps'),
    (r'\bmind alteration\b', 'mind conditioning'),
    (r'\bDefense Cyborgs\b', 'Defense Machines'),
    (r'\bdefense cyborgs\b', 'Defense Machines'),
    (r'\bdefense machines\b', 'Defense Machines'),
    (r'\bflying cyborgs\b', 'flying machines'),
    (r'\bCyborg Soldiers\b', 'Machine Soldiers'),
    (r'\bCyborg Soldier\b', 'Machine Soldier'),
    (r'\bDivine Nation of Assyria\b', 'Holy Nation of Assyria'),
    (r'\bancient god race\b', 'Ancient Gods'),
    (r'\bItemology\b', 'Item Studies'),
    (r'\bitem studies\b', 'Item Studies'),
    (r'\bvolcano plateau\b', 'Volcano Plateau'),
    (r'\bglacier plateau\b', 'Glacier Plateau'),
    (r'\bwasteland plateau\b', 'Wasteland Plateau'),
    (r'\bthe Slaying Knight\b', 'the Slaughter Knight'),
    (r'\bZodiac Twelve Gods ring\b', 'ring of the Zodiac Twelve Gods'),
    (r'\bheavy gun\b(?! batter)', 'heavy MG'),
    # 機改 = machine (this world's spelling), never "cyborg"
    (r'\bCyborgs\b', 'Machines'),
    (r'\bCyborg\b', 'Machine'),
    (r'\bcyborgs\b', 'machines'),
    (r'\bcyborg\b', 'machine'),
]

files = [p for p in sorted(glob.glob('work/translation/en/scenes/[KS]???.json'))]
drafts = sorted(glob.glob('work/translation/en/drafts/*.py'))
total = {pat: 0 for pat, _ in FIX}
samples = {pat: [] for pat, _ in FIX}


def fix(s, where):
    for pat, rep in FIX:
        new, n = re.subn(pat, rep, s)
        if n:
            total[pat] += n
            if len(samples[pat]) < 3:
                samples[pat].append((where, s[:90]))
            s = new
    return s


for p in files:
    rows = json.load(open(p, encoding='utf-8'))
    changed = False
    for r in rows:
        if r['en']:
            new = fix(r['en'], r['id'])
            if new != r['en']:
                r['en'] = new
                changed = True
    if changed and not dry:
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
scene_total = dict(total)
for p in drafts:
    s = open(p, encoding='utf-8').read()
    new = fix(s, p[-7:-3])
    if new != s and not dry:
        open(p, 'w', encoding='utf-8').write(new)
for pat, rep in FIX:
    if total[pat]:
        print('%4d (scene rows %4d)  %s -> %s' % (total[pat], scene_total[pat], pat, rep))
        for w, s in samples[pat]:
            print('       ', w, s)
print('dry run' if dry else 'applied')
