"""Disassemble the EXE or an overlay: python tools/disasm.py EXE|O001|O020 start_addr count"""
import sys, os, struct
import capstone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD = {'O001': 0x800F07E0, 'O002': 0x8011888C, 'O020': 0x8011888C}


def image(name):
    if name == 'EXE':
        return open(os.path.join(ROOT, 'work/source/disc/SLPS_014.79'), 'rb').read()[0x800:], 0x80010000
    return open(os.path.join(ROOT, 'work/source/ovl/%s.bin' % name[1:]), 'rb').read(), LOAD[name]


def dis(name, start, n):
    d, base = image(name)
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    o = start - base
    for i in md.disasm(d[o:o + 4 * n], start):
        print('%08x  %-8s %s' % (i.address, i.mnemonic, i.op_str))


if __name__ == '__main__':
    dis(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3]))
