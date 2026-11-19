"""Scan files for Shift-JIS runs. Usage: sjis_scan.py file [minchars] -> counts; writes runs to stdout as offset + text (utf-8)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def is_lead(b): return 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xea
def is_trail(b): return 0x40 <= b <= 0xfc and b != 0x7f

def runs(d, minch=3, allow_ascii=True):
    i = 0; n = len(d); out = []
    while i < n:
        j = i; dbl = 0
        while j < n:
            b = d[j]
            if is_lead(b) and j + 1 < n and is_trail(d[j+1]):
                try:
                    d[j:j+2].decode('cp932')
                except Exception:
                    break
                # restrict to common ranges: 81-84, 88-9f, e0-ea
                if 0x85 <= b <= 0x87: break
                j += 2; dbl += 1
            elif allow_ascii and (0x20 <= b < 0x7f or 0xa1 <= b <= 0xdf) and dbl:
                j += 1
            else:
                break
        if dbl >= minch:
            out.append((i, d[i:j]))
            i = j
        else:
            i += 1
    return out

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    minch = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    r = runs(d, minch)
    print(f"# {sys.argv[1]}: {len(r)} runs, {sum(len(x[1]) for x in r)} bytes")
    if len(sys.argv) > 3:
        for off, b in r:
            print(f"{off:08x} {b.decode('cp932', 'replace')}")
