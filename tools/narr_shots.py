"""Render overlay-20 narration blocks (epilogues, town descriptions) in game through the telegram's
narration printer and save each page: boots through name entry over GDB (tools/gdbdbg.py), waits
for the telegram, then for every block points the printer's text at it (struct at *(0x80062884)
+0x5C, index *(0x80062610)+0xA = 1), resets the pen and the glyph buffer, presses Circle at page
waits and grabs the screen.

    python tools/narr_shots.py <out dir> <file offset> ...     (offsets in overlay 20, hex)
Needs the test emulator running on a fresh boot (tools/emu.ps1 start <cue>).
"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdbdbg

L = 0x8011888C
ROUTE = ("wait 300; press start; wait 120; press start; wait 200; press start; wait 200; press start; "
         "wait 200; press circle; wait 240; press start; wait 300; press circle; wait 240; press start; "
         "wait 60; press circle; wait 90; press circle; wait 240; press start; wait 60; press circle; "
         "wait 90; press circle")


def main(out, offs):
    D = gdbdbg.Dbg()
    for tok in ROUTE.split(';'):
        a = tok.split()
        D.press(a[1]) if a[0] == 'press' else D.wait(int(a[1]))
    for _ in range(600):
        D.wait(1)
        p = struct.unpack('<I', D.g.read(0x80062884, 4))[0]
        if 0x80000000 <= p < 0x80200000 and struct.unpack('<I', D.g.read(p + 0x5C, 4))[0] == 0x80167000:
            break
    # the printer's own task struct: 0x80062610 is the running task, so read it inside the printer
    D.g.cmd('Z0,80121348,4')
    while True:
        D.g.s.sendall(b'$c#63')
        D.g._recv_packet()
        r = D.regs()
        if r[37] == 0x80121348:
            task = struct.unpack('<I', D.g.read(0x80062610, 4))[0]
            break
    D.g.cmd('z0,80121348,4')
    print('task', hex(task))
    rect = (0, 0, 320, 240)
    for off in offs:
        D.g.write(p + 0x5C, struct.pack('<I', L + off))
        bx, by = struct.unpack('<2H', D.g.read(0x801667B8, 4))
        if off >= 0x46000:                 # town descriptions: the town printer's own start (0x2E, 0x12)
            bx, by = 0x2E, 0x12
        D.g.write(0x801667BC, struct.pack('<2H', bx, by))
        for i in range(200):
            D.g.write(0x800D5560 + 12 * i, b'\0')
        D.g.write(task + 0xA, struct.pack('<H', 1))
        page = 0
        for f in range(6000):
            D.wait(1)
            idx = struct.unpack('<H', D.g.read(task + 0xA, 2))[0]
            if not 1 <= idx < 0x8000:
                print('printer left the block', hex(idx))
                break
            w = struct.unpack('<H', D.g.read(L + off + 2 * (idx - 1), 2))[0]
            if w in (0xFFFC, 0xFFFF):
                D.wait(3)
                pix = D.grab(*rect)
                name = os.path.join(out, '%05x_%d.png' % (off, page))
                gdbdbg.write_png(name, rect[2], rect[3], pix)
                print(name, hex(w))
                page += 1
                if w == 0xFFFF:
                    break
                D.press('circle')
    D.close()


if __name__ == '__main__':
    main(sys.argv[1], [int(x, 16) for x in sys.argv[2:]])
