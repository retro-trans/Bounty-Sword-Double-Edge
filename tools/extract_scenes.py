"""Extract dialogue rows from the event files (KIVE.BIN = K###, SIVE.BIN = S###). Ported from Bounty Sword First.

Output: work/translation/en/scenes/S<nnn>.json  (working files, contain Japanese: never commit;
tools/strip_jp.py writes the committable *.en.json copies).
Row: id, off/end (file offsets of the run), block, spk (speaker op+id), kind, jp, en.
Tags in text: {n} newline(8005)  {hero:N} player name(8009)  {name:N} (800a)  {w:N} pause(8019)
              {num:a,b} (802d)  {8031}  {var} run-time name (8057, battle lines)
"""
import json, os, sys, glob, hashlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import Scene, check
from bs2_text import CM

INLINE = {0x8005: lambda a: '{n}', 0x8009: lambda a: '{hero:%d}' % a[0], 0x800a: lambda a: '{name:%d}' % a[0],
          0x8019: lambda a: '{w:%d}' % a[0], 0x8057: lambda a: '{var}', 0x800c: lambda a: '{800c}', 0x802d: lambda a: '{num:%d,%d}' % (a[0], a[1]), 0x8031: lambda a: '{8031}'}
SPK = {0x804f, 0x8002, 0x8064, 0x8068, 0x8061, 0x8033, 0x8024}
BANK = {3: 'scene', 6: 'battle', 7: 'bank7', 0: 'orphan'}

def rows_of(path):
    s, toks, bad = check(path)
    assert not bad, (path, bad)
    n = int(os.path.basename(path)[:3]); pre = 'K' if 'kive' in path else 'S'; rows = []
    starts = sorted(b for b in s.blocks if b)
    cur = []; spk = None; in_choice = 0; after66 = False
    def flush(endoff):
        nonlocal cur
        # trim leading/trailing inline ops
        while cur and cur[0][1] == 'op': cur.pop(0)
        while cur and cur[-1][1] == 'op': cur.pop()
        if cur and any(t[1] == 'g' and t[2] for t in cur):
            txt = ''.join(CM[t[2]] if t[1] == 'g' else INLINE[t[2]](t[3]) for t in cur)
            off = cur[0][0]; end = cur[-1][0] + 2 + 2 * len(cur[-1][3])
            blk = max([i for i, b in enumerate(s.blocks) if b and b <= off] or [0], key=lambda i: s.blocks[i])
            bank = next((BANK[x[0]] for x in s.sections if x[2] <= off < x[3]), '?')
            rows.append(dict(id='%s%03d_%04d' % (pre, n, len(rows)), off=off, end=end, block=blk, bank=bank,
                             spk=spk, kind='data?' if after66 else ('choice' if in_choice else 'dlg'), jp=txt, en=''))
        cur = []
    for off, k, v, a in toks:
        if k == 'g' or (k == 'op' and v in INLINE):
            cur.append((off, k, v, a)); continue
        flush(off)
        if v == 0x8008: in_choice = a[1]
        elif v == 0x8006 and in_choice: in_choice -= 1
        if v in SPK: spk = '%04x:%s' % (v, ','.join('%x' % x for x in a))
        after66 = (v == 0x8066) or (after66 and v in (0x8066,))
        if v in (0x8003, 0x8007, 0x8020, 0x8004): pass
    flush(s.end)
    return rows

if __name__ == '__main__':
    out = 'work/translation/en/scenes'; os.makedirs(out, exist_ok=True)
    tot = 0; chars = 0; uniq = set()
    only = set(sys.argv[1:])       # optional: write only these scenes (K012 S003 ...)
    for fn in sorted(glob.glob('work/source/kive/*.bin')) + sorted(glob.glob('work/source/sive/*.bin')):
        name = ('K' if 'kive' in fn else 'S') + os.path.basename(fn)[:3]
        if only and name not in only: continue
        if os.path.getsize(fn) < 0x100: continue
        if not Scene(fn).has_script: continue
        rows = rows_of(fn)
        dst = os.path.join(out, name + '.json')
        if os.path.exists(dst):      # keep existing translations
            old = {r['id']: r for r in json.load(open(dst, encoding='utf-8'))}
            for r in rows:
                if r['id'] in old and old[r['id']]['jp'] == r['jp']: r['en'] = old[r['id']].get('en', '')
        json.dump(rows, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        tot += len(rows); chars += sum(len(r['jp']) for r in rows); uniq.update(r['jp'] for r in rows)
    print('rows', tot, 'chars', chars, 'unique rows', len(uniq), 'unique chars', sum(len(x) for x in uniq))
