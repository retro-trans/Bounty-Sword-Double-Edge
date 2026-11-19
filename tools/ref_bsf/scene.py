"""Scene file (WINBIN 33..116) script parser.

The section at header+0x0C is a table of u32 file offsets to script blocks, then a stream of
u16 tokens: glyphs (< 0x52B), opcodes 0x8000..0x806F with fixed arguments, 0xFFFF.
Argument spec per opcode: 'w' = one word, 'O' = u32 file offset (jump target), 'D' = u32 value.
"""
import struct, sys, os, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsf_text import CM, NGLYPH

ARGS = {
 0x8000: '', 0x8001: '', 0x8002: 'w', 0x8003: '', 0x8004: '', 0x8005: '', 0x8006: '', 0x8007: '',
 0x8008: '', 0x8009: 'w', 0x800a: 'w', 0x800b: 'ww', 0x800e: 'www', 0x8010: 'D', 0x8011: 'D',
 0x8012: 'w', 0x8014: 'wO', 0x8015: 'wO', 0x8016: 'O', 0x8017: 'w', 0x8018: 'w', 0x8019: 'w',
 0x801b: 'wO', 0x801c: 'wO', 0x801f: 'w', 0x8020: '', 0x8025: 'w', 0x802d: 'ww', 0x802e: '', 0x802f: 'w', 0x8032: '', 0x8034: '', 0x803a: '', 0x8057: '',
 0x8030: 'w', 0x8031: '', 0x8035: 'D', 0x8036: 'ww', 0x8037: 'ww', 0x8038: 'O', 0x8039: '',
 0x803b: 'wwO', 0x803c: 'wwO', 0x803d: '', 0x803e: 'ww', 0x8040: 'wwO', 0x8041: 'wwO', 0x8042: 'wwO',
 0x8044: 'w', 0x8047: 'wwwwwwwww', 0x804c: 'wO', 0x804b: 'wO', 0x804d: 'DO', 0x804e: 'DO', 0x804f: 'w', 0x8052: '', 0x8053: 'w',
 0x8054: 'w', 0x8055: '', 0x8056: '', 0x8058: 'w', 0x805a: 'ww', 0x805b: 'w', 0x805c: 'O', 0x805d: 'O',
 0x8060: 'w', 0x8061: 'www', 0x8062: 'wO', 0x8063: 'wO', 0x8064: 'w', 0x8065: 'w', 0x8066: '',
 0x8067: 'w', 0x8068: 'ww', 0x806a: '', 0x806b: '', 0x806c: '', 0x806d: '', 0x806e: 'wwww', 0x806f: 'w',
}

class Scene:
    """Script banks: header slot 3 (scene dialogue), 6 and 7 (common battle lines and another
    bank). Each bank = table of u32 file offsets (ends where its first block starts) + token stream."""
    BANKS = (3, 6, 7)

    def __init__(self, path):
        self.path = path; self.d = open(path, 'rb').read()
        self.hdr = struct.unpack_from('<12I', self.d, 0)
        self.sections = []           # (bank slot, table offset, stream start, stream end)
        self.blocks = []             # every table entry, all banks
        self.block_pos = []          # file offset of each table entry
        bounds = sorted(set(x for x in self.hdr if x) | {len(self.d)})
        for slot in self.BANKS:
            tab = self.hdr[slot]
            if not tab: continue
            end = min(x for x in bounds if x > tab)
            q = tab; first = end
            while q < first:
                v = struct.unpack_from('<I', self.d, q)[0]
                if v: first = min(first, v)
                self.blocks.append(v); self.block_pos.append(q); q += 4
            self.sections.append((slot, tab, first, end))
        self.has_script = bool(self.sections)
        self.tab = self.sections[0][1] if self.sections else 0
        self.start = self.sections[0][2] if self.sections else 0
        self.end = self.sections[-1][3] if self.sections else 0
        self.nblk = len(self.blocks)
        self.ends = {x[3] for x in self.sections}

    def tokens(self):
        """yield (offset, kind, value, args) ; kind: 'g' glyph, 'op', 'x' unknown"""
        out = []
        for slot, tab, start, end in self.sections:
            self._tokens(start, end, out)
        return out

    def _tokens(self, p, end_, out):
        d = self.d
        while p < end_:
            w = struct.unpack_from('<H', d, p)[0]
            if w < NGLYPH: out.append((p, 'g', w, ())); p += 2
            elif w == 0x8008:
                # choice menu: 4 header words (x?, count, ?, width), `count` strings each ended by 8006, then count jump offsets
                h = struct.unpack_from('<4H', d, p + 2); out.append((p, 'op', w, h)); q = p + 10; n = 0
                while n < h[1]:
                    v = struct.unpack_from('<H', d, q)[0]
                    if v == 0x8006: out.append((q, 'op', v, ())); n += 1
                    elif v < NGLYPH: out.append((q, 'g', v, ()))
                    else: out.append((q, 'x', v, ()))
                    q += 2
                for _ in range(h[1]):
                    out.append((q, 'op', 0x8016 | 0x10000, (('O', struct.unpack_from('<I', d, q)[0]),))); q += 4
                p = q
            elif w in ARGS:
                a = []; q = p + 2
                for c in ARGS[w]:
                    if c == 'w': a.append(struct.unpack_from('<H', d, q)[0]); q += 2
                    else: a.append((c, struct.unpack_from('<I', d, q)[0])); q += 4
                out.append((p, 'op', w, tuple(a))); p = q
            elif w < 0x8000: out.append((p, 'd', w, ())); p += 2      # data word (small tables in bank 7)
            else: out.append((p, 'x', w, ())); p += 2
        return out

def check(path):
    s = Scene(path); toks = s.tokens(); starts = {t[0] for t in toks}
    bad = collections.Counter()
    for b in s.blocks:
        if b and b not in starts: bad['block'] += 1
    for off, k, v, a in toks:
        if k == 'x': bad['unk %04x' % v] += 1
        for x in a:
            if isinstance(x, tuple) and x[0] == 'O' and x[1] not in starts and x[1] not in s.ends: bad['jump from %04x' % v] += 1
    return s, toks, bad

if __name__ == '__main__':
    tot = collections.Counter()
    for fn in sorted(glob.glob('work/source/winbin/*.bin')):
        n = int(fn[-7:-4])
        if n < 33 or os.path.getsize(fn) < 0x100: continue
        s, toks, bad = check(fn)
        tot.update(bad)
        if bad and len(sys.argv) > 1: print(n, dict(bad))
    print(tot.most_common(60))
