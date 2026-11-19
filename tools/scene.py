"""Event file (KIVE.BIN / SIVE.BIN entries) script parser. Ported from the Bounty Sword First tools.

The section at header+0x0C is a table of u32 file offsets to script blocks, then a stream of
u16 tokens: glyphs (< 0x52B), opcodes 0x8000..0x806F with fixed arguments, 0xFFFF.
Argument spec per opcode: 'w' = one word, 'O' = u32 absolute RAM address of a jump target (file offset + BASE),
'F' = u32 file-relative jump target, 'D' = u32 value. Parsed operands of kind O and F are both returned as
('O'|'F', file offset).
"""
import struct, sys, os, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bs2_text import CM, NGLYPH

BASE = 0x8010C84C   # RAM address of file offset 0; every 'O' operand is an absolute address

ARGS = {
 0x8033: 'w', 0x8024: 'w', 0x803f: 'w', 0x8070: '', 0x800c: '', 0x8021: '', 0x8072: 'wwO', 0x800d: 'ww',
 0x8000: '', 0x8001: '', 0x8002: 'w', 0x8003: '', 0x8004: '', 0x8005: '', 0x8006: '', 0x8007: '',
 0x8008: '', 0x8009: 'w', 0x800a: 'w', 0x800b: 'ww', 0x800e: 'www', 0x8010: 'D', 0x8011: 'D',
 0x8012: 'w', 0x8014: 'wO', 0x8015: 'wO', 0x8016: 'O', 0x8017: 'w', 0x8018: 'w', 0x8019: 'w',
 0x801b: 'wO', 0x801c: 'wO', 0x801f: 'w', 0x8020: '', 0x8025: 'w', 0x802d: 'ww', 0x802e: '', 0x802f: 'w', 0x8032: '', 0x8034: '', 0x803a: '', 0x8057: '',
 0x8030: 'w', 0x8031: '', 0x8035: 'D', 0x8036: 'ww', 0x8037: 'ww', 0x8038: 'F', 0x8039: '',
 0x803b: 'wwO', 0x803c: 'wwO', 0x803d: '', 0x803e: 'ww', 0x8040: 'wwO', 0x8041: 'wwO', 0x8042: 'wwO',
 0x8044: 'w', 0x8047: 'wwwwwwwww', 0x804c: 'wO', 0x804b: 'wO', 0x804d: 'DF', 0x804e: 'DF', 0x804f: 'w', 0x8052: '', 0x8053: 'w',
 0x8054: 'w', 0x8055: '', 0x8056: '', 0x8058: 'w', 0x805a: 'ww', 0x805b: 'w', 0x805c: 'O', 0x805d: 'O',
 0x8060: 'w', 0x8061: 'www', 0x8062: 'wwO', 0x8063: 'wwO', 0x8064: 'w', 0x8065: 'w', 0x8066: '',
 0x8067: 'w', 0x8068: 'ww', 0x806a: '', 0x806b: '', 0x806c: '', 0x806d: '', 0x806e: 'wwww', 0x806f: 'w',
}

class Scene:
    """Script banks: header slot 3 (scene dialogue), 6 and 7 (common battle lines and another
    bank). Each bank = table of u32 file offsets (ends where its first block starts) + token stream."""
    BANKS = (3, 6, 7)

    def __init__(self, path):
        self.path = path; self.d = open(path, 'rb').read()
        self.hdr = struct.unpack_from('<18I', self.d, 0)
        self.stream_end = {}         # section end -> real end of the token stream when data follows it
        self.sections = []           # (bank slot, table offset, stream start, stream end)
        self.blocks = []             # every table entry, all banks
        self.block_pos = []          # file offset of each table entry
        bounds = sorted(set(x for x in self.hdr if x) | {len(self.d)})
        banks = [(slot, self.hdr[slot]) for slot in self.BANKS if self.hdr[slot]]
        # a bank at 0x48 that no header slot points at (copy of the common bank, e.g. KIVE 003, 119): slot 0
        if len(self.d) > 0x50 and 0x48 not in self.hdr and struct.unpack_from('<I', self.d, 0x48)[0] == 0                 and 0x48 < struct.unpack_from('<I', self.d, 0x4c)[0] < len(self.d):
            banks.insert(0, (0, 0x48))
        for slot, tab in banks:
            end = min(x for x in bounds if x > tab)
            q = tab; first = end
            while q < first:
                v = struct.unpack_from('<I', self.d, q)[0]
                if v: first = min(first, v)
                self.blocks.append(v); self.block_pos.append(q); q += 4
            self.sections.append((slot, tab, first, end))
        self._split_embedded()
        self.has_script = bool(self.sections)
        self.tab = self.sections[0][1] if self.sections else 0
        self.start = self.sections[0][2] if self.sections else 0
        self.end = self.sections[-1][3] if self.sections else 0
        self.nblk = len(self.blocks)
        self.ends = {x[3] for x in self.sections}

    def _split_embedded(self):
        """Some files carry further banks inside what the header calls one bank: after a block's
        end comes another table of u32 file offsets and its stream (copies of the common banks that
        no header slot points at, e.g. K023, K109, K119). The first non-glyph data word marks such a
        table; it starts 4 bytes earlier with a zero entry. They become banks of slot 0."""
        d = self.d
        i = 0
        while i < len(self.sections):
            slot, tab, st, en = self.sections[i]
            out = []
            self._tokens(st, en, out)
            t = next((x for x in out if x[1] == 'd'), None)
            if t is not None:
                # walk back over entries small enough to look like glyphs, to the zero entry that opens the table
                T = (t[0] & ~3) - 4
                while T > st and struct.unpack_from('<I', d, T)[0] != 0 and T < struct.unpack_from('<I', d, T)[0] < en:
                    T -= 4
                v = struct.unpack_from('<I', d, t[0] & ~3)[0]
                if T >= st and T % 4 == 0 and struct.unpack_from('<I', d, T)[0] == 0 and t[0] < v < en:
                    q = T; first = en; pos = []; vals = []
                    while q < first:
                        e = struct.unpack_from('<I', d, q)[0]
                        if e: first = min(first, e)
                        vals.append(e); pos.append(q); q += 4
                    if all(e == 0 or T < e <= en for e in vals):
                        self.sections[i] = (slot, tab, st, T)
                        self.sections.insert(i + 1, (0, T, first, en))
                        # table entries are kept in file order: insert after this bank's entries
                        k = sum((x[2] - x[1]) // 4 for x in self.sections[:i + 1])
                        self.blocks[k:k] = vals; self.block_pos[k:k] = pos
                        if en in self.stream_end:
                            pass
            self.stream_end.pop(en, None) if False else None
            i += 1

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
                    elif v in (0x8009, 0x800a): out.append((q, 'op', v, (struct.unpack_from('<H', d, q + 2)[0],))); q += 2
                    else: out.append((q, 'x', v, ()))
                    q += 2
                for _ in range(h[1]):
                    out.append((q, 'op', 0x8016 | 0x10000, (('F', struct.unpack_from('<I', d, q)[0]),))); q += 4
                p = q
            elif w in ARGS:
                a = []; q = p + 2
                for c in ARGS[w]:
                    if c == 'w': a.append(struct.unpack_from('<H', d, q)[0]); q += 2
                    else:
                        v = struct.unpack_from('<I', d, q)[0]
                        a.append((c, v - BASE if c == 'O' else v)); q += 4
                out.append((p, 'op', w, tuple(a))); p = q
            elif w < 0x8000: out.append((p, 'd', w, ())); p += 2      # data word (small tables in bank 7)
            else:
                # not script: an unlisted data table follows the stream (e.g. KIVE 119). Cut the stream back to
                # the end of the last opcode; the words after it stay where they are.
                while out and out[-1][1] != 'op': out.pop()
                self.stream_end[end_] = (out[-1][0] + self._size(out[-1])) if out else p
                break
        return out

    def _size(self, t):
        return 2 + sum(2 if not isinstance(x, tuple) else 4 for x in t[3]) if t[2] != (0x8016 | 0x10000) else 4

def check(path):
    s = Scene(path); toks = s.tokens(); starts = {t[0] for t in toks}
    bad = collections.Counter()
    for b in s.blocks:
        if b and b not in starts: bad['block'] += 1
    for off, k, v, a in toks:
        if k == 'x': bad['unk %04x' % v] += 1
        for x in a:
            if isinstance(x, tuple) and x[0] in 'OF' and x[1] not in starts and x[1] not in s.ends and x[1] not in s.stream_end.values(): bad['jump from %04x' % v] += 1
    return s, toks, bad

if __name__ == '__main__':
    tot = collections.Counter()
    for fn in sorted(glob.glob('work/source/kive/*.bin') + glob.glob('work/source/sive/*.bin')):
        n = fn[-12:-4]
        if os.path.getsize(fn) < 0x100: continue
        s, toks, bad = check(fn)
        tot.update(bad)
        if bad and len(sys.argv) > 1: print(n, dict(bad))
    print(tot.most_common(60))
