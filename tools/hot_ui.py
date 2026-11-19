"""Write translated UI rows (text only) into the running game, for testing without a rebuild/reboot.

    python tools/hot_ui.py EXE O001 O020 ...

Only the bytes of translated rows are written (never code or variables), and only when RAM still
holds the original Japanese for that row (so an overlay that is not loaded is left alone).
Overlay load addresses: O001 0x800F07E0, O002 / O020 0x8011888C. Stops at the pad breakpoint.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdbdbg
import ui_insert

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD = {'O001': 0x800F07E0, 'O002': 0x8011888C, 'O020': 0x8011888C}


def source(name):
    if name == 'EXE':
        return open(os.path.join(ROOT, 'work/source/disc/SLPS_014.79'), 'rb').read(), 0x80010000 - 0x800
    return open(os.path.join(ROOT, 'work/source/ovl/%s.bin' % name[1:]), 'rb').read(), LOAD[name]


if __name__ == '__main__':
    d = gdbdbg.Dbg()
    try:
        d.step_frame(0)
        for name in sys.argv[1:]:
            src, base = source(name)
            keep = [(0x2FDA0, 0x30110)] if name == 'O020' else ()
            new, n = ui_insert.patch(name, src, keep)
            w = skip = 0
            for r in ui_insert.load(name):
                if not r['en'] or r['en'] == ui_insert.SKIP:
                    continue
                o = r['off'] + 2 * r['raw_prefix']
                ln = 2 * r['slots']
                if new[o:o + ln] == src[o:o + ln]:
                    continue
                if d.g.read(base + o, ln) != src[o:o + ln]:
                    skip += 1
                    continue
                d.g.write(base + o, new[o:o + ln])
                w += 1
            print(name, 'written', w, 'skipped (RAM differs)', skip)
    finally:
        d.close()
