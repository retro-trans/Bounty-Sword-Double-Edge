"""Build the English test disc.

    python tools/build.py [--no-disc]

Steps
  1. OVLFILE.BIN   entry 1 (main overlay): dialogue VWF + packed-token fetch in the free area at
                   0x801014D8, patch sites listed in tools/hooks.py
  2. BIN/WIN.BIN   entry 0: English glyphs drawn into the font page (tools/enfont.py), same size
  3. BIN/KIVE.BIN, BIN/SIVE.BIN   every event file that has translated rows is rebuilt by
                   tools/relink.py (script banks laid out again with packed English and a per-file
                   word dictionary; checked against the original op for op) and the archive is
                   written again with its offset table
  4. disc image    a file is replaced in place when it is no larger than its original sector
                   span; a larger one is written after the last sector of the image and its
                   directory record is updated (the game opens these files by name)

Output: work/output/BountySword2-en-v<VERSION>.bin/.cue, files also in work/output/files/.
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enfont
import fontgrad
import hooks
import nameentry
import relink
import ui_insert
import bs2_text
from build_disc import Disc

VERSION = '0.3.19'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'source', 'disc')
OUT = os.path.join(ROOT, 'work', 'output')
SRC_BIN = os.path.join(ROOT, 'Bounty Sword - Double Edge (Japan).bin')
GAP = 4          # every archive entry is followed by 4 zero bytes


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
        exp = h['expect_ovl'].get(a)       # None: data whose original is checked elsewhere (name table)
        assert exp is None or bytes(d[off(a):off(a) + len(exp)]) == exp, hex(a)
        d[off(a):off(a) + len(b)] = b
    sec20, size20 = struct.unpack_from('<II', d, 20 * 8)   # entry 20: title, name entry, opening telegram
    p20 = dict(nameentry.patches())
    p20.update(nameentry.telegram_patches(h['sym']))
    p20.update(nameentry.day_patches())
    for o, (old_b, new_b) in p20.items():
        p = sec20 * 2048 + o
        assert o + len(new_b) <= size20 and bytes(d[p:p + len(old_b)]) == old_b, hex(o)
        d[p:p + len(new_b)] = new_b
    keep20 = O020_KEEP + [(o, o + len(nb)) for o, (ob, nb) in p20.items()]
    keep1 = [(a - hooks.OVL1_LOAD, a - hooks.OVL1_LOAD + len(b)) for a, b in h['patches_ovl'].items()]
    keep1.append((hooks.OVL_BASE - hooks.OVL1_LOAD, hooks.OVL_BASE - hooks.OVL1_LOAD + hooks.OVL_ROOM))
    count = struct.unpack_from('<I', d, 0)[0] // 8
    for n in range(1, count):
        sec_n, size_n = struct.unpack_from('<II', d, n * 8)
        if not size_n:
            continue
        p = sec_n * 2048
        keep = keep20 if n == 20 else (keep1 if n == 1 else ())
        body, k = ui_insert.patch('O%03d' % n, bytes(d[p:p + size_n]), keep)
        if k:
            d[p:p + size_n] = body
            UI_LOG.append('UI O%03d: %d rows' % (n, k))
    return bytes(d)


def patch_exe():
    """Menu VWF + pair expansion (tools/hooks.py build_exe); same size, replaced in place."""
    d = bytearray(open(os.path.join(SRC, 'SLPS_014.79'), 'rb').read())
    e = hooks.build_exe()

    def off(a):
        return a - 0x80010000 + 0x800
    for a, b in e['patches'].items():
        exp = e['expect'][a]
        assert bytes(d[off(a):off(a) + len(exp)]) == exp, hex(a)
        d[off(a):off(a) + len(b)] = b
    d, n = ui_insert.patch('EXE', bytes(d))
    UI_LOG.append('UI EXE: %d rows' % n)
    return d


UI_LOG = []
# overlay 20 areas owned by other patches or read by the narration printers (no pair expansion there)
O020_KEEP = [(0x2FDA0, 0x30110)]


def patch_win():
    d = bytearray(open(os.path.join(SRC, 'BIN', 'WIN.BIN'), 'rb').read())
    o = enfont.PAGE_OFF
    assert struct.unpack_from('<I', d, o - 20)[0] == 0x12
    d[o:o + 0x8000] = fontgrad.page(enfont.patch(bytes(d[o:o + 0x8000])))
    offs = struct.unpack_from('<104I', d, 0)
    d = bytearray(fontgrad.cluts(bytes(d), offs))           # two-tone gradient (tools/fontgrad.py)
    starts = sorted(set(x for x in offs if x)) + [len(d)]
    for n in (5, 76, 77):
        a = offs[n]
        b = starts[starts.index(a) + 1]
        body, k = ui_insert.patch('W%03d' % n, bytes(d[a:b]))
        if k:
            d[a:b] = body
            UI_LOG.append('UI W%03d: %d rows' % (n, k))
    return bytes(d)


def pack_archive(d, ents, data):
    """Write the archive again. Entries are written in their original physical order; the bytes
    between one entry's end and the next entry (4 zero bytes, in one place an unreferenced chunk)
    are copied as they are; entries that share an offset still share it.
    Header: u32 header size, u32 end of data, (offset, size) per entry."""
    hs = struct.unpack_from('<I', d, 0)[0]
    out = bytearray(d[:hs])
    distinct = sorted(set(o for o, s in ents if s))
    size_of = {}
    for i, (o, s) in enumerate(ents):
        if s:
            assert size_of.setdefault(o, s) == s, 'entries share an offset with different sizes'
    owner = {}
    for i, (o, s) in enumerate(ents):
        if s:
            owner.setdefault(o, i)
    new_off = {}
    prev_end = hs
    for o in distinct:
        out += d[prev_end:o] if o >= prev_end else b''
        while len(out) % 4:
            out.append(0)
        new_off[o] = len(out)
        # an aliased entry uses the rebuilt data of whichever index was rebuilt (all the same file)
        cand = [data[i] for i, e in enumerate(ents) if e[0] == o and e[1]]
        changed = [c for c in cand if c != d[o:o + size_of[o]]]
        out += changed[0] if changed else cand[0]
        prev_end = max(prev_end, o + size_of[o])
    out += d[prev_end:]
    end = struct.unpack_from('<I', d, 4)[0]
    struct.pack_into('<I', out, 4, len(out) - (len(d) - end))
    for i, (o, s) in enumerate(ents):
        if s:
            cand = [data[j] for j, e in enumerate(ents) if e[0] == o and e[1]]
            changed = [c for c in cand if c != d[o:o + size_of[o]]]
            struct.pack_into('<II', out, 8 + i * 8, new_off[o], len(changed[0] if changed else cand[0]))
    return bytes(out)


def build_events(arc, prefix, folder, log):
    d = open(os.path.join(SRC, 'BIN', arc), 'rb').read()
    ents = bs2_text.archive(d)
    data = {i: d[o:o + s] for i, (o, s) in enumerate(ents) if s}
    assert pack_archive(d, ents, data) == d, 'archive writer does not reproduce the original ' + arc
    done = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'translation', 'en', 'scenes', prefix + '*.json'))):
        if p.endswith('.en.json'):
            continue
        rows = json.load(open(p, encoding='utf-8'))
        if not any(r['en'] for r in rows):
            continue
        name = os.path.basename(p)[:4]
        idx = int(name[1:])
        src = os.path.join(ROOT, 'work', 'source', folder, '%03d.bin' % idx)
        out, rep, info = relink.fit(src, rows)
        problems = relink.verify(src, out, info)
        assert not problems, (name, problems)
        issues = {k: v for k, v in rep.items() if isinstance(v, list) and v}
        log.append('%s %5d -> %5d bytes, %4d rows + %d menus, dictionary %3d words (%d bytes), banks %5d/%5d%s%s' % (
            name, os.path.getsize(src), rep['size'], rep['rows'], rep['choices'], rep['dict_words'], rep['dict_bytes'],
            rep['region_used'], rep['region'],
            ', %d bank(s) continue after the file end' % rep['overflow'] if rep['overflow'] else '',
            ' ISSUES %s' % issues if issues else ''))
        data[idx] = out
        done += 1
    new = pack_archive(d, ents, data)
    log.append('%s %d -> %d bytes, %d event files rebuilt' % (arc, len(d), len(new), done))
    return new, done


def main():
    log = []
    h = hooks.build()
    files = [('SLPS_014.79', patch_exe()), ('OVLFILE.BIN', patch_ovl(h)), ('BIN/WIN.BIN', patch_win())]
    log.append('hooks: overlay 1 %d/%d bytes at %08X' % (len(h['ovl_blob']), hooks.OVL_ROOM, hooks.OVL_BASE))
    log.extend(UI_LOG)
    for arc, pre, folder in (('KIVE.BIN', 'K', 'kive'), ('SIVE.BIN', 'S', 'sive')):
        data, n = build_events(arc, pre, folder, log)
        if n:
            files.append(('BIN/' + arc, data))
    for path, data in files:
        dst = os.path.join(OUT, 'files', path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
    if '--no-disc' not in sys.argv:
        name = 'BountySword2-en-v%s' % VERSION
        dst = os.path.join(OUT, name + '.bin')
        disc = Disc.open_copy(SRC_BIN, dst)
        before = disc.nsectors
        for path, data in files:
            moved = disc.replace(path, data)
            e = disc.entries[path.upper()]
            log.append('disc: %-14s lba %6d size %8d %s' % (path, e.lba, e.size, 'MOVED to the end of the image' if moved else 'in place'))
        after = disc.nsectors
        disc.close()
        open(os.path.join(OUT, name + '.cue'), 'w').write('FILE "%s.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % name)
        log.append('disc: %d -> %d sectors: %s' % (before, after, dst))
    open(os.path.join(OUT, 'build_v%s.log' % VERSION), 'w').write('\n'.join(log) + '\n')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
