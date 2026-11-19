"""Find pointer tables to FFFF-terminated glyph strings in a RAM dump.

    python tools/ptrscan.py <ram.bin> [lo hi]     (addresses hex, default whole RAM)

A string start is a 2-aligned address holding plausible text (glyph codes < 0x52B,
FFFE newlines) ended by FFFF.  A table is a run of >= 2 consecutive words that each point
at such a string.  Prints: table address, entry count, lowest/highest target, total words.
No text is printed.
"""
import struct
import sys

d = open(sys.argv[1], 'rb').read()
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x80010000
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x80200000
N = len(d)


def strlen(a):
    """Words in the string at address a (incl. FFFF), or 0 if it is not text."""
    o = a & 0x1FFFFF
    n = 0
    while o + 1 < N and n < 400:
        w = d[o] | d[o + 1] << 8
        n += 1
        if w == 0xFFFF:
            return n if n > 1 else 0
        if not (w < 0x52B or w == 0xFFFE or 0xFF00 <= w < 0xFFF0):
            return 0
        o += 2
    return 0


def main():
    a = lo
    out = []
    while a < hi:
        o = a & 0x1FFFFF
        run = []
        while a < hi:
            w = struct.unpack_from('<I', d, a & 0x1FFFFF)[0]
            if not (0x80010000 <= w < 0x80200000) or w & 1:
                break
            n = strlen(w)
            if not n:
                break
            run.append((w, n))
            a += 4
        if len(run) >= 2:
            t = a - 4 * len(run)
            out.append((t, run))
        a += 4 if not run else 0
        if run and len(run) < 2:
            pass
    for t, run in out:
        ts = [w for w, _ in run]
        print('%08X  n=%-4d  targets %08X..%08X  words %d' % (t, len(run), min(ts), max(ts), sum(n for _, n in run)))


main()
