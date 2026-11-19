"""Minimal ISO9660 reader/writer helpers for PS1 MODE2/2352 images."""
import struct, os, sys

SECTOR = 2352
HDR = 24      # sync(12)+header(4)+subheader(8)
DATA = 2048

class Image:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        self.size = os.path.getsize(path)
        self.nsec = self.size // SECTOR

    def raw(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)

    def sector(self, lba):
        return self.raw(lba)[HDR:HDR + DATA]

    def subheader(self, lba):
        return self.raw(lba)[16:24]

    def read(self, lba, size):
        out = bytearray()
        n = (size + DATA - 1) // DATA
        for i in range(n):
            out += self.sector(lba + i)
        return bytes(out[:size])

    def pvd(self):
        return self.sector(16)

    def root(self):
        p = self.pvd()
        rec = p[156:156 + 34]
        return struct.unpack('<I', rec[2:6])[0], struct.unpack('<I', rec[10:14])[0]

    def listdir(self, lba, size):
        data = self.read(lba, size)
        i = 0
        out = []
        while i < len(data):
            ln = data[i]
            if ln == 0:
                i = (i // DATA + 1) * DATA
                continue
            rec = data[i:i + ln]
            elba, esz = struct.unpack('<I', rec[2:6])[0], struct.unpack('<I', rec[10:14])[0]
            flags = rec[25]
            nl = rec[32]
            name = rec[33:33 + nl]
            if name not in (b'\x00', b'\x01'):
                out.append(dict(name=name.decode('ascii').split(';')[0], lba=elba, size=esz,
                                dir=bool(flags & 2), rec_off=i, dir_lba=lba))
            i += ln
        return out

    def walk(self, lba=None, size=None, prefix=''):
        if lba is None:
            lba, size = self.root()
        for e in self.listdir(lba, size):
            e['path'] = prefix + e['name']
            yield e
            if e['dir']:
                yield from self.walk(e['lba'], e['size'], e['path'] + '/')

if __name__ == '__main__':
    img = Image(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    for e in img.walk():
        sh = img.subheader(e['lba'])
        print('%-40s lba=%6d size=%9d %s sub=%s' % (e['path'], e['lba'], e['size'], 'D' if e['dir'] else ' ', sh.hex()))
        if out:
            p = os.path.join(out, e['path'])
            if e['dir']:
                os.makedirs(p, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                form2 = sh[2] & 0x20
                if not form2:
                    open(p, 'wb').write(img.read(e['lba'], e['size']))
