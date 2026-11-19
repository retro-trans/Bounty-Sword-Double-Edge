"""Map code addresses from Bounty Sword First (sibling project, same engine) to this game by
instruction signature: opcode + registers are compared, immediates and jump targets are ignored.
    python tools/sigmap.py <addr> [<addr> ...]      (addresses in the sibling's EXE / overlay 1)
"""
import struct, sys
SIB = 'E:/Projects/Bounty Sword First/work/source/'

def mask(w):
    op = w >> 26
    if op == 0: return w
    if op in (2, 3): return op << 26
    return w & 0xffff0000

def load(path, base, skip=0):
    d = open(path, 'rb').read()[skip:]
    ws = struct.unpack_from('<%dI' % (len(d) // 4), d)
    return base, [mask(w) for w in ws]

def imgs():
    import glob, os
    sib_ovl1 = [p for p in glob.glob(SIB + 'ovl/*') if os.path.basename(p).startswith(('001', 'ovl001', '01'))]
    return ([load(SIB + 'disc/SLPS_007.57', 0x80010000, 0x800)] + ([load(sib_ovl1[0], 0x80108EEC)] if sib_ovl1 else []),
            [load('work/source/disc/SLPS_014.79', 0x80010000, 0x800), load('work/source/ovl/001.bin', 0x800F07E0)])

def find(addr, n=12, back=0):
    sib, our = imgs()
    for base, ws in sib:
        i = (addr - base) // 4 - back
        if 0 <= i < len(ws) - n:
            sig = ws[i:i + n]
            res = []
            for b2, w2 in our:
                for j in range(len(w2) - n):
                    if w2[j] == sig[0] and w2[j:j + n] == sig: res.append(b2 + (j + back) * 4)
            return res
    return None

if __name__ == '__main__':
    for a in sys.argv[1:]:
        a = int(a, 16)
        for n, back in ((12, 0), (8, 0), (12, 6), (8, 4), (6, 0), (6, 3)):
            r = find(a, n, back)
            if r is None: print('%08x not in sibling images' % a); break
            if len(r) == 1: print('%08x -> %08x (n=%d back=%d)' % (a, r[0], n, back)); break
        else:
            print('%08x -> ambiguous/none %s' % (a, [hex(x) for x in (r or [])][:6]))
