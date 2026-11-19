"""Bounty Sword First text encoding helpers (16-bit glyph indices + control words)."""
import json, os, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CM = {int(k, 16): v for k, v in json.load(open(os.path.join(ROOT, 'tools', 'charmap.json'), encoding='utf-8')).items()}
NGLYPH = 0x52b
KANA = set(range(0xa1, 0x141))

def decode_words(ws):
    s = ''
    for v in ws:
        s += CM.get(v, '{%04x}' % v) if v < NGLYPH else '<%04x>' % v
    return s

def scan_runs(d, minlen=3, align=2):
    """Find runs of words that look like text: glyphs with at least `minlen` chars and some kana/kanji."""
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
            out.append((i*2, ws[i:j])); i = j
        else: i += 1
    return out
