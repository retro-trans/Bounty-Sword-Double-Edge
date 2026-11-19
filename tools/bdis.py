"""Disassemble this game's code:  bdis.py exe|ovlN <addr> [count]   |   bdis.py exe|ovlN xref <addr>
Overlay load addresses: 1 -> 0x800F07E0, 2 and 20 -> 0x8011888C (others: pass base as 4th arg)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdis
OVL_BASE = {1: 0x800F07E0, 2: 0x8011888C, 20: 0x8011888C}

class Ovl(mdis.Img):
    def __init__(self, n, base=None):
        self.d = open('work/source/ovl/%03d.bin' % n, 'rb').read(); self.base = base or OVL_BASE[n]

def img(name):
    return mdis.Img('work/source/disc/SLPS_014.79') if name == 'exe' else Ovl(int(name[3:]))

if __name__ == '__main__':
    im = img(sys.argv[1])
    if sys.argv[2] == 'xref':
        for a, k in mdis.xref(im, int(sys.argv[3], 16)): print('%08x %s' % (a, k))
    else:
        print('\n'.join(mdis.dis(im, int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 40)))
