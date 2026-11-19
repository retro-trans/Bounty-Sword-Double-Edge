"""Which rows share one translation, and which scene owns it.

A row's key decides whose translation is copied where (tools/propagate.py):
  * rows of the common banks (battle / bank7 / orphan), choices, and scene rows of 8+ characters:
    the source text alone;
  * shorter scene rows mean different things in different places, so they only match a row with
    the same text, the same speaker op and the same neighbouring rows (variant copies of a scene).
The owner of a key is its first row in scene order (K000.. then S000..). Only the owner's scene
translates it; every other copy is filled by propagation.

    python tools/rowkeys.py        writes work/translation/en/owners.json  {row id: owner row id}
"""
import glob
import json
import os

SCENES = 'work/translation/en/scenes'


def scene_files():
    f = sorted(glob.glob(SCENES + '/K*.json')) + sorted(glob.glob(SCENES + '/S*.json'))
    return [p for p in f if not p.endswith('.en.json')]


def keys_for(rows):
    out = []
    for i, r in enumerate(rows):
        common = r.get('bank', 'scene') != 'scene'
        if common or r['kind'] == 'choice' or len(r['jp']) >= 8:
            out.append(('t', r['kind'], r['jp']))      # the same text shares one translation in every bank
        else:
            prev = rows[i - 1]['jp'] if i else ''
            nxt = rows[i + 1]['jp'] if i + 1 < len(rows) else ''
            out.append(('c', r['kind'], r['jp'], r['spk'], prev, nxt))
    return out


def owners():
    own = {}
    res = {}
    for p in scene_files():
        rows = json.load(open(p, encoding='utf-8'))
        for r, k in zip(rows, keys_for(rows)):
            own.setdefault(k, r['id'])
            res[r['id']] = own[k]
    return res


if __name__ == '__main__':
    o = owners()
    json.dump(o, open('work/translation/en/owners.json', 'w'), indent=0)
    mine = sum(1 for k, v in o.items() if k == v)
    print('rows', len(o), 'owned (to translate)', mine)
    per = {}
    for k, v in o.items():
        if k == v:
            per[k[:4]] = per.get(k[:4], 0) + 1
    print('scenes with owned rows', len(per))
