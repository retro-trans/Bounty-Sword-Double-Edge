"""Scan files for Shift-JIS text runs (full-width + half-width kana + ASCII). Counts only to console;
full text goes to a UTF-8 file (kept out of git under work/source)."""
import sys, os, json

def is_lead(b): return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xea
def is_trail(b): return 0x40 <= b <= 0xfc and b != 0x7f

def runs(data, minchars=3):
    i = 0; n = len(data)
    while i < n:
        j = i; dbl = 0; cnt = 0
        while j < n:
            b = data[j]
            if is_lead(b) and j + 1 < n and is_trail(data[j+1]):
                # restrict to plausible rows: 81-84 symbols/kana, 88-9f,e0-ea kanji
                if 0x85 <= b <= 0x87: break
                j += 2; dbl += 1; cnt += 1
            elif 0x20 <= b <= 0x7e or 0xa1 <= b <= 0xdf:
                j += 1; cnt += 1
            else:
                break
        if dbl >= minchars:
            try:
                s = data[i:j].decode('cp932')
                yield i, j - i, s
            except UnicodeDecodeError:
                pass
        i = j + 1 if j == i else j

if __name__ == '__main__':
    root = sys.argv[1]; out = sys.argv[2]
    res = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            data = open(p, 'rb').read()
            r = [(o, l, s) for o, l, s in runs(data)]
            rel = os.path.relpath(p, root).replace(chr(92), '/')
            res[rel] = [dict(off=o, len=l, text=s) for o, l, s in r]
            print('%-20s size=%9d runs=%6d chars=%7d' % (rel, len(data), len(r), sum(len(s) for _, _, s in r)))
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
