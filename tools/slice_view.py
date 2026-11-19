"""Write a compact view of a scene's rows for translating: slice_view.py K000 [start end] -> work/source/dump/view_<scene>.txt"""
import json, sys
sc = sys.argv[1]; rows = json.load(open('work/translation/en/scenes/%s.json' % sc, encoding='utf-8'))
sp = {e['id']: e for e in json.load(open('work/glossary/speakers.json', encoding='utf-8'))}
own = json.load(open('work/translation/en/owners.json'))
a = int(sys.argv[2]) if len(sys.argv) > 2 else 0; b = int(sys.argv[3]) if len(sys.argv) > 3 else len(rows)
with open('work/source/dump/view_%s.txt' % sc, 'w', encoding='utf-8') as f:
    for r in rows[a:b]:
        who = ''
        if r['spk']:
            op, arg = r['spk'].split(':'); i = int(arg.split(',')[0], 16)
            who = '%s[%s]' % (sp[i]['en'] if i in sp else '?%d' % i, op)
        f.write('%s b%d %s %s | %s%s\n' % (r['id'], r['block'], r['kind'], who, r['jp'], ('  => ' + r['en']) if r['en'] else ('' if own.get(r['id'], r['id']) == r['id'] else '  (SKIP: copy of %s)' % own[r['id']])))
print(len(rows))
