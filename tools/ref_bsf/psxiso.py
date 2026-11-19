"""Minimal PS1 MODE2/2352 ISO9660 reader/writer helpers."""
import struct, os, sys

SECTOR = 2352
HDR = 24  # sync(12)+header(4)+subheader(8)
DATA = 2048


class Disc:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.f.seek(0, 2)
        self.nsec = self.f.tell() // SECTOR

    def raw(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)

    def read(self, lba, size):
        out = bytearray()
        n = (size + DATA - 1) // DATA
        for i in range(n):
            self.f.seek((lba + i) * SECTOR + HDR)
            out += self.f.read(DATA)
        return bytes(out[:size])

    def _dir(self, lba, size, prefix, out):
        d = self.read(lba, size)
        p = 0
        while p < len(d):
            ln = d[p]
            if ln == 0:
                p = (p // DATA + 1) * DATA
                continue
            rec = d[p:p + ln]
            elba, esz = struct.unpack_from('<I4xI', rec, 2)
            flags = rec[25]
            nl = rec[32]
            name = rec[33:33 + nl]
            if name not in (b'\x00', b'\x01'):
                nm = name.decode('ascii').split(';')[0]
                full = prefix + nm
                if flags & 2:
                    out.append(dict(name=full, lba=elba, size=esz, dir=True, recpos=None))
                    self._dir(elba, esz, full + '/', out)
                else:
                    out.append(dict(name=full, lba=elba, size=esz, dir=False,
                                    rec_lba=lba + p // DATA, rec_off=p % DATA))
            p += ln

    def files(self):
        pvd = self.read(16, DATA)
        assert pvd[1:6] == b'CD001'
        root = pvd[156:190]
        lba, sz = struct.unpack_from('<I4xI', root, 2)
        out = []
        self._dir(lba, sz, '', out)
        return out

    def is_form2(self, lba):
        return bool(self.raw(lba)[18] & 0x20)


if __name__ == '__main__':
    d = Disc(sys.argv[1])
    outdir = sys.argv[2] if len(sys.argv) > 2 else None
    for e in d.files():
        f2 = (not e['dir']) and e['size'] and d.is_form2(e['lba'])
        print(f"{e['lba']:7d} {e['size']:10d} {'D' if e['dir'] else ('X' if f2 else ' ')} {e['name']}")
        if outdir:
            p = os.path.join(outdir, e['name'])
            if e['dir']:
                os.makedirs(p, exist_ok=True)
            elif not f2:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(d.read(e['lba'], e['size']))
