"""Bounty Sword Double Edge text encoding helpers (16-bit glyph indices + control words).
Script code == glyph index in the font page (WIN.BIN entry 0); see tools/font.py."""
import json, os, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'work', 'glossary', 'charmap.json'), encoding='utf-8')).items()}
NGLYPH = 0x52b
KANA = set(range(81, 243))

def decode_words(ws):
    s = ''
    for v in ws:
        s += CM.get(v, '{%04x}' % v) if v < NGLYPH else '<%04x>' % v
    return s

def archive(d):
    """KIVE/SIVE: u32 header size, u32 total size, then (u32 offset, u32 size) per entry."""
    hs, tot = struct.unpack_from('<II', d, 0)
    return [struct.unpack_from('<II', d, 8 + i * 8) for i in range((hs - 8) // 8)]

def scan_runs(d, minlen=3):
    n = len(d) // 2; ws = struct.unpack_from('<%dH' % n, d)
    out = []; i = 0
    while i < n:
        j = i; txt = 0; kana = 0
        while j < n:
            v = ws[j]
            if v < NGLYPH:
                if v: txt += 1
                if v in KANA: kana += 1
            elif v >= 0x8000: pass
            else: break
            j += 1
        if txt >= minlen and kana >= 2 and ws[i] != 0:
            out.append((i * 2, ws[i:j])); i = j
        else: i += 1
    return out
