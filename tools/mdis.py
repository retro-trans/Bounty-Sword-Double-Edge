"""MIPS disassembly helpers for SLPS_007.57 / RAM dumps.
  mdis.py <file> <addr> [count]          disassemble (file: exe or 2MB ram dump)
  mdis.py <file> xref <addr>             find lui/addiu|ori|load pairs and jal referencing addr
  mdis.py <file> str <text>              find ascii string, print address
"""
import struct, sys
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

class Img:
    def __init__(self, path):
        d = open(path, 'rb').read()
        if d[:8] == b'PS-X EXE':
            self.base = struct.unpack_from('<I', d, 0x18)[0]; self.d = d[0x800:]
        elif len(d) == 0x200000:
            self.base = 0x80000000; self.d = d
        else:
            self.base = int(sys.argv[-1], 16) if False else 0; self.d = d
    def off(self, a): return (a & 0x1fffffff) - (self.base & 0x1fffffff)
    def w(self, a): return struct.unpack_from('<I', self.d, self.off(a))[0]
    def bytes(self, a, n): o = self.off(a); return self.d[o:o+n]

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)

def dis(img, a, n=40):
    out = []
    for i in md.disasm(img.bytes(a, n*4), a):
        out.append('%08x  %-8s %s' % (i.address, i.mnemonic, i.op_str))
    return out

def xref(img, target, lo=None, hi=None):
    d = img.d; n = len(d)//4; res = []
    ws = struct.unpack_from('<%dI' % n, d)
    jal = 0x0c000000 | ((target >> 2) & 0x3ffffff); j = 0x08000000 | ((target >> 2) & 0x3ffffff)
    reg_hi = {}
    for i, w in enumerate(ws):
        a = img.base + i*4
        if w == jal: res.append((a, 'jal'))
        elif w == j: res.append((a, 'j'))
        elif w == target: res.append((a, 'word'))
        op = w >> 26
        if op == 0x0f: reg_hi[(w >> 16) & 31] = ((w & 0xffff) << 16, i)
        elif op in (9, 0x0d, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2b):
            rs = (w >> 21) & 31
            if rs in reg_hi and i - reg_hi[rs][1] < 12:
                imm = w & 0xffff
                v = (reg_hi[rs][0] | imm) if op == 0x0d else (reg_hi[rs][0] + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xffffffff
                if v == target: res.append((a, 'ref op%02x' % op))
    return res

if __name__ == '__main__':
    img = Img(sys.argv[1])
    if sys.argv[2] == 'xref':
        for a, k in xref(img, int(sys.argv[3], 16)): print('%08x %s' % (a, k))
    elif sys.argv[2] == 'str':
        s = sys.argv[3].encode(); o = 0
        while True:
            o = img.d.find(s, o)
            if o < 0: break
            print('%08x' % (img.base + o)); o += 1
    else:
        print('\n'.join(dis(img, int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 40)))
