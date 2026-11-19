"""Build the English test disc.

    python tools/build.py [--no-disc]

Steps
  1. SLPS_007.57   cursor-path VWF hook + width table in the free area at 0x8005DEE0, one jal changed
  2. OVLFILE.BIN   entry 1 (main overlay): dialogue/telop VWF + packed-token fetch in the free area
                   at 0x80128838, patch sites listed in tools/hooks.py; entry 20: one call changed
  3. WIN/WINBIN.BIN  entry 0: English glyphs drawn into the font page (tools/enfont.py);
                   scene entries with translated rows rebuilt (tools/relink.py: script banks
                   laid out again with packed English and a per-scene word dictionary; checked
                   against the original op for op); offset table rewritten
  4. disc image    SLPS and OVLFILE are replaced in place (same size). WINBIN is replaced in
                   place when it is no larger than the original (the relinked scenes keep their
                   size); only if it grew is it written after the last sector of the image

Output: work/output/BountySwordFirst-en-v<VERSION>.bin/.cue, files also in work/output/files/.
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont
import hooks
import insert_scenes
import relink
from build_disc import Disc

VERSION = '0.2.0'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'source', 'disc')
OUT = os.path.join(ROOT, 'work', 'output')
SRC_BIN = os.path.join(ROOT, 'Bounty Sword First (Japan).bin')
EXE_LOAD = 0x80010000


def patch_exe(h):
    d = bytearray(open(os.path.join(SRC, 'SLPS_007.57'), 'rb').read())

    def off(a):
        return a - EXE_LOAD + 0x800
    o = off(hooks.EXE_BASE)
    assert not any(d[o:o + hooks.EXE_ROOM]), 'EXE free area is not empty'
    d[o:o + len(h['exe_blob'])] = h['exe_blob']
    for a, b in h['patches_exe'].items():
        exp = h['expect_exe'].get(a)
        assert exp is None or bytes(d[off(a):off(a) + len(exp)]) == exp, hex(a)
        d[off(a):off(a) + len(b)] = b
    return bytes(d)


def patch_ovl(h):
    d = bytearray(open(os.path.join(SRC, 'OVLFILE.BIN'), 'rb').read())
    sec, size = struct.unpack_from('<II', d, 8)          # entry 1
    base = sec * 2048

    def off(a):
        o = a - hooks.OVL1_LOAD
        assert 0 <= o < size
        return base + o
    o = off(hooks.OVL_BASE)
    assert not any(d[o:o + hooks.OVL_ROOM]), 'overlay free area is not empty'
    d[o:o + len(h['ovl_blob'])] = h['ovl_blob']
    for a, b in h['patches_ovl'].items():
        exp = h['expect_ovl'].get(a)
        assert exp is None or bytes(d[off(a):off(a) + len(exp)]) == exp, hex(a)
        d[off(a):off(a) + len(b)] = b
    sec20, size20 = struct.unpack_from('<II', d, 20 * 8)   # entry 20: opening narration / save overlay
    for o20, b in h['patches_ovl20'].items():
        p = sec20 * 2048 + o20
        assert o20 < size20 and bytes(d[p:p + 4]) == h['expect_ovl20'][o20], hex(o20)
        d[p:p + len(b)] = b
    return bytes(d)


def build_winbin(log):
    d = open(os.path.join(SRC, 'WIN', 'WINBIN.BIN'), 'rb').read()
    n = struct.unpack_from('<I', d, 0)[0] // 4
    offs = list(struct.unpack_from('<%dI' % n, d, 0))
    distinct = sorted(set(o for o in offs if o))
    end_of = {o: (distinct[i + 1] if i + 1 < len(distinct) else len(d)) for i, o in enumerate(distinct)}
    data = {o: bytearray(d[o:end_of[o]]) for o in distinct}

    # entry 0: font page
    e0 = data[offs[0]]
    page_off = 0x48 + 0x14
    assert struct.unpack_from('<I', e0, 0x48)[0] == 0x12
    e0[page_off:page_off + 0x8000] = enfont.patch(bytes(e0[page_off:page_off + 0x8000]))

    # scenes
    done = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'translation', 'en', 'scenes', 'S*.json'))):
        if p.endswith('.en.json'):
            continue
        rows = json.load(open(p, encoding='utf-8'))
        if not any(r['en'] for r in rows):
            continue
        idx = int(os.path.basename(p)[1:4])
        src = os.path.join(ROOT, 'work', 'source', 'winbin', '%03d.bin' % idx)
        out, rep, info = relink.fit(src, rows)
        problems = relink.verify(src, out, info)
        assert not problems, (idx, problems)
        issues = {k: v for k, v in rep.items() if isinstance(v, list) and v}
        log.append('S%03d %5d -> %5d bytes, %3d rows + %d menus, dictionary %3d words, bank region %5d/%5d%s%s' % (
            idx, os.path.getsize(src), rep['size'], rep['rows'], rep['choices'], rep['dict_words'],
            rep['region_used'] + (rep['dict_bytes'] if rep.get('dict_in_region') else 0), rep['region'],
            ', continues after the file end' if rep['overflow'] else '',
            ' ISSUES %s' % issues if issues else ''))
        data[offs[idx]] = bytearray(out)
        done += 1

    # rebuild: same order, same aliasing (entries that shared an offset still do)
    new_off = {}
    blob = bytearray(n * 4)
    for o in distinct:
        while len(blob) % 4:
            blob.append(0)
        new_off[o] = len(blob)
        blob += data[o]
    struct.pack_into('<%dI' % n, blob, 0, *[new_off[o] if o else 0 for o in offs])
    log.append('WINBIN %d -> %d bytes, %d scene entries rebuilt' % (len(d), len(blob), done))
    return bytes(blob)


def main():
    log = []
    h = hooks.build()
    exe = patch_exe(h)
    ovl = patch_ovl(h)
    win = build_winbin(log)
    os.makedirs(os.path.join(OUT, 'files', 'WIN'), exist_ok=True)
    open(os.path.join(OUT, 'files', 'SLPS_007.57'), 'wb').write(exe)
    open(os.path.join(OUT, 'files', 'OVLFILE.BIN'), 'wb').write(ovl)
    open(os.path.join(OUT, 'files', 'WIN', 'WINBIN.BIN'), 'wb').write(win)
    log.append('hooks: exe %d/%d bytes at %08X, overlay %d/%d bytes at %08X' % (
        len(h['exe_blob']), hooks.EXE_ROOM, hooks.EXE_BASE, len(h['ovl_blob']), hooks.OVL_ROOM, hooks.OVL_BASE))
    if '--no-disc' not in sys.argv:
        name = 'BountySwordFirst-en-v%s' % VERSION
        dst = os.path.join(OUT, name + '.bin')
        disc = Disc.open_copy(SRC_BIN, dst)
        before = disc.nsectors
        for path, data in (('SLPS_007.57', exe), ('OVLFILE.BIN', ovl), ('WIN/WINBIN.BIN', win)):
            moved = disc.replace(path, data)
            e = disc.entries[path.upper()]
            log.append('disc: %-16s lba %6d size %8d %s' % (path, e.lba, e.size, 'MOVED to the end of the image' if moved else 'in place'))
        after = disc.nsectors
        disc.close()
        open(os.path.join(OUT, name + '.cue'), 'w').write('FILE "%s.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % name)
        log.append('disc: %d -> %d sectors: %s' % (before, after, dst))
    open(os.path.join(OUT, 'build_v%s.log' % VERSION), 'w').write('\n'.join(log) + '\n')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
