"""Write the current hook code into the running game (a savestate made with older hooks).

    python tools/hotpatch.py

Halts at the pad read (once per frame, outside the text interpreter), writes the EXE and
overlay hook blobs and every patch site to RAM, then resumes. Scene data is not touched:
scenes are loaded from the disc image the emulator runs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdbdbg
import hooks

h = hooks.build()
d = gdbdbg.Dbg()
try:
    d.step_frame(0)
    d.g.write(hooks.EXE_BASE, h['exe_blob'])
    d.g.write(hooks.OVL_BASE, h['ovl_blob'])
    for a, b in list(h['patches_exe'].items()) + list(h['patches_ovl'].items()):
        d.g.write(a, b)
    print('hot-patched: exe %d bytes, overlay %d bytes, %d sites' % (
        len(h['exe_blob']), len(h['ovl_blob']), len(h['patches_exe']) + len(h['patches_ovl'])))
finally:
    d.close()
