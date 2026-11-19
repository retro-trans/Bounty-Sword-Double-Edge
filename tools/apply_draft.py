"""Apply a draft (work/translation/en/drafts/<scene>.py, dict EN: row index -> text) to the scene file.

    apply_draft.py K000 [--dry]

Checks, per row:
  * tags other than {n} must match the source row exactly;
  * every character must exist in the English font (tools/enfont.py: letters, digits,
    space and  ! ? : ( ) / & % + - = ~ , . ' " ;  -- nothing else: no ellipsis glyph,
    no asterisk, no accented letters, no curly quotes);
  * line width in pixels: 236 (the dialogue is drawn 4 px right of the box edge) (dialogue and narration alike; the narration path has not been
    measured in this game yet); a name tag counts 12 px per character;
  * at most 3 lines per page (or as many as the source row if it has more);
  * at most 150 visible glyphs per page.
Rows not in the draft are left alone (rows already filled by propagation stay).
Nothing is written while any problem remains.
"""
import json
import os
import re
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont

sc = sys.argv[1]
dry = '--dry' in sys.argv
EN = runpy.run_path('work/translation/en/drafts/%s.py' % sc)['EN']
p = 'work/translation/en/scenes/%s.json' % sc
rows = json.load(open(p, encoding='utf-8'))
W = enfont.widths()
tag = re.compile(r'\{[^}]*\}')
FW_SPACE = chr(0x3000)
JP_QUOTE = chr(0x300C)
problems = 0


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


n = 0
for i, t in sorted(EN.items()):
    if not (0 <= i < len(rows)):
        print('NO SUCH ROW', i)
        problems += 1
        continue
    r = rows[i]
    if r['kind'] == 'data?':
        print('DATA ROW, do not translate', r['id'])
        problems += 1
        continue
    jt = sorted(x for x in tag.findall(r['jp']) if x != '{n}')
    et = sorted(x for x in tag.findall(t) if x != '{n}')
    if jt != et:
        print('TAG MISMATCH', r['id'], 'source', jt, 'draft', et)
        problems += 1
    bad = sorted(set(c for c in tag.sub('', t) if c not in enfont.ENC))
    if bad:
        print('NO GLYPH for %r' % ''.join(bad), r['id'])
        problems += 1
        continue
    telop = r['kind'] == 'dlg' and not r['jp'].lstrip(FW_SPACE + ' ').startswith((JP_QUOTE, chr(0x300E)))
    limit = 236
    lines = t.split('{n}')
    vis = 0
    for ln in lines:
        px, v = measure(ln.strip(' ') if telop else ln)
        vis += v
        if px > limit:
            print('WIDE %d px (max %d)' % (px, limit), r['id'], ln)
            problems += 1
    if r['kind'] == 'dlg' and len(lines) > max(3, r['jp'].count('{n}') + 1):
        print('LINES %d' % len(lines), r['id'])
        problems += 1
    if r['kind'] == 'choice' and '{n}' in t:
        print('CHOICE WITH LINE BREAK', r['id'])
        problems += 1
    if vis > 150:
        print('GLYPHS %d (max 150)' % vis, r['id'])
        problems += 1
    r['en'] = t
    n += 1
own = json.load(open('work/translation/en/owners.json'))
left = [r['id'] for r in rows if not r['en'] and r['kind'] != 'data?' and own.get(r['id'], r['id']) == r['id']]
print('%s: rows %d, in draft %d, problems %d, still empty %d %s' % (sc, len(rows), n, problems, len(left), left[:8]))
if dry:
    pass
elif problems:
    print('NOT applied: fix the problems first')
else:
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('applied')
