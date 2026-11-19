"""Put the English rows back into a scene file (WINBIN 33..116).

Constraints found in the game:
  * a scene file is loaded at 0x8013B2B8 and overlay 4 is loaded right behind the
    scene buffer at 0x801452BC, so a scene can never exceed 40,964 bytes (LIMIT);
  * all script offsets are file-relative, and text is inline between opcodes.

So nothing is squeezed into its old place and nothing existing moves:
  * each translated unit is written somewhere else in the file and its old place gets
    `8016 <new offset>` (jump); the new copy ends with `8016 <old end>` (jump back);
  * 'somewhere else' is first a hole left by an already moved unit (the Japanese text
    behind its 6-byte jump), else the end of the file;
  * English letters are packed two per token (tools/hooks.py, pair table), which the
    patched interpreter expands.

A row whose packed English is no longer than its Japanese run is written in place (padded
with null ops). Otherwise it is moved as a unit:
Unit = [speaker op if it directly precedes the text][text run][8003 if it directly follows].
A run too short to hold a jump is moved together with the next row when only plain ops
sit between them (item-name inserts).
Both jumps then sit between messages, where the original script also uses 8016.
If a block start or jump target points into the unit, it falls back to the text run
alone; if that fails too the row stays Japanese and is reported.

Telop blocks (a block that starts with unquoted text: narration, chapter cards) are
read linearly from the block table entry by a routine that neither follows jumps nor expands
pairs. For those the whole block is rewritten as a linear copy at the end of the file (plain
glyph tokens, same ops in the same order) and the block table entry is repointed; the
original block is left untouched. Each line keeps the placement of its Japanese line:
centred lines are centred, others keep their left indent (TELOP_WIDTH pixels wide).

Choice menus (8008) are moved whole (header, choice texts, jump table); their text is
not packed because the menu routine reads it directly. Header word 4 (width in glyphs)
is set to the longest English choice.

A page may show at most MAX_GLYPHS visible glyphs: the game's glyph pool has 128 slots
and no overflow check.

    build_scene(path, rows) -> (bytes, report)
    python tools/insert_scenes.py S033        report only
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import check
from enfont import encode, ENC
from hooks import pack_pairs

SPEAKER_OPS = {0x8002, 0x804F, 0x8064, 0x8061, 0x8068}
TAG = re.compile(r'\{([^}]*)\}')
LIMIT = 0x801452BC - 0x8013B2B8
MAX_GLYPHS = 110
SPACE = ENC[' ']
TELOP_CELL = 13                # the narration printer advances 13 px per full-width glyph
TELOP_WIDTH = 19 * TELOP_CELL  # a telop line is 19 full-width cells


def telop_lines(jp, en):
    """English text of a telop row -> glyph codes per line, padded like the Japanese line."""
    import enfont
    w = enfont.widths()
    jl = jp.split('{n}')
    el = [x.strip(' ') for x in en.split('{n}')]
    out = []
    wide = []
    for i, line in enumerate(el):
        j = jl[i] if i < len(jl) else jl[-1]
        core = j.strip('　')
        left = len(j) - len(j.lstrip('　'))
        right = len(j) - len(j.rstrip('　'))
        codes, _vis = encode_row(line, pack=False)        # tags become their opcodes
        px = sum(w.get(c, 0) for c in codes if c < 0x8000) + 72 * len(TAG.findall(line))
        if not core:
            pad = 0
        elif left >= 2 and abs(left - right) <= 2:
            pad = max(0, (TELOP_WIDTH - px) // 2)            # centred in the source
        else:
            pad = left * TELOP_CELL                           # left aligned with the source indent
        if pad + px > TELOP_WIDTH:
            wide.append((i, pad + px))
        out.append([0] * (pad // TELOP_CELL) + [SPACE] * ((pad % TELOP_CELL) // 4) + codes)
    return out, wide


def encode_row(text, pack=True):
    """-> (tokens, visible glyph count)"""
    out = []
    visible = 0

    def run(s):
        nonlocal visible
        codes = encode(s)
        visible += sum(1 for c in codes if c != SPACE)
        return pack_pairs(codes) if pack else codes

    pos = 0
    for m in TAG.finditer(text):
        out += run(text[pos:m.start()])
        t = m.group(1)
        if t == 'n':
            out.append(0x8005)
        elif t.startswith('hero:'):
            out += [0x8009, int(t[5:])]
            visible += int(t[5:])
        elif t.startswith('name:'):
            out += [0x800A, int(t[5:])]
            visible += int(t[5:])
        elif t.startswith('w:'):
            out += [0x8019, int(t[2:])]
        elif t.startswith('num:'):
            a, b = t[4:].split(',')
            out += [0x802D, int(a), int(b)]
            visible += 6
        elif t == '8031':
            out.append(0x8031)
        elif t == 'var':
            out.append(0x8057)
            visible += 6
        else:
            raise ValueError('unknown tag {%s}' % t)
        pos = m.end()
    out += run(text[pos:])
    return out, visible


def tok_len(t):
    n = 2
    for a in t[3]:
        n += 4 if isinstance(a, tuple) else 2
    return n


def build_scene(path, rows):
    s, toks, bad = check(path)
    assert not bad, bad
    d = bytearray(s.d)
    while len(d) % 4:
        d += b'\x00'
    by_off = {t[0]: i for i, t in enumerate(toks)}
    targets = set(b for b in s.blocks if b)
    for t in toks:
        for a in t[3]:
            if isinstance(a, tuple) and a[0] == 'O':
                targets.add(a[1])
    report = {'moved': 0, 'in_place': 0, 'merged': 0, 'choices': 0, 'in_holes': 0, 'telop_blocks': 0, 'skipped': [], 'no_room': [],
              'too_many_glyphs': [], 'telop_wide': []}
    holes = []          # [start, end) free ranges inside the original file

    def words(ws):
        return b''.join(struct.pack('<H', w) for w in ws)

    def jump(pos, to):
        """8016 <to> written at file offset pos. The game reads the operand with a word load,
        so it must be 4-byte aligned (as every 32-bit operand in the original scripts is):
        a null op (8000) goes in front when needed."""
        if (pos + 2) % 4:
            return struct.pack('<HHI', 0x8000, 0x8016, to)
        return struct.pack('<HI', 0x8016, to)

    def need(pos):
        return len(jump(pos, 0))

    def clear(a, b):
        return not any(a < t < b for t in targets)

    def place(make):
        """make(offset) -> blob. Returns the offset used, or None when the file is full."""
        best = None
        for h in holes:
            size = len(make(h[0]))
            if h[1] - h[0] >= size and (best is None or h[1] - h[0] < best[1] - best[0]):
                best = h
        if best:
            off = best[0]
            blob = make(off)
            d[off:off + len(blob)] = blob
            best[0] += len(blob)
            report['in_holes'] += 1
            return off
        off = len(d)
        if off + len(make(off)) > LIMIT:
            return None
        d.extend(make(off))
        while len(d) % 4:
            d.append(0)
        return off

    def release(start, end):
        """The old unit [start, end) now begins with a jump; the rest is free."""
        a = start + need(start)
        if end - a >= 8 and clear(start, end):
            holes.append([a, end])

    # ---- telop blocks: linear copy + block table repoint ----
    starts = sorted(set(b for b in s.blocks if b))
    telop_rows = set()
    row_at = {r['off']: r for r in rows}
    for bi, bstart in enumerate(starts):
        i0 = by_off[bstart]
        # telop = block that begins with unquoted text (narration, title cards). A block that
        # begins with an opening quote is dialogue run by the interpreter (hero monologues, all
        # the battle-bank lines): those take the packed unit path below.
        if toks[i0][1] != 'g' or toks[i0][2] == 0x05:
            continue
        bend = min([e for e in sorted(s.ends) + starts if e > bstart])
        i1 = i0
        while i1 < len(toks) and toks[i1][0] < bend:
            i1 += 1
        mine = [r for r in rows if bstart <= r['off'] < bend and r['kind'] == 'dlg']
        for r in mine:
            telop_rows.add(r['id'])
        if not any(r['en'] for r in mine):
            continue
        out = bytearray()
        base = len(d)
        k = i0
        while k < i1:
            t = toks[k]
            r = row_at.get(t[0]) if t[1] == 'g' else None
            if r is not None and r['kind'] == 'dlg' and r['en']:
                lines, wide = telop_lines(r['jp'], r['en'])
                for x in wide:
                    report['telop_wide'].append((r['id'],) + x)
                enc = []
                for n_line, codes in enumerate(lines):
                    if n_line:
                        enc.append(0x8005)
                    enc += codes
                out += words(enc)
                while k < i1 and toks[k][0] < r['end']:
                    k += 1
                continue
            raw = bytes(s.d[t[0]:t[0] + tok_len(t)])
            if t[1] == 'op' and any(isinstance(a, tuple) for a in t[3]):
                # keep 32-bit operands 4-byte aligned in the copy
                first32 = 2
                for c in __import__('scene').ARGS.get(t[2] & 0xFFFF, ''):
                    if c != 'w':
                        break
                    first32 += 2
                if (base + len(out) + first32) % 4:
                    out += words([0x8000])
            out += raw
            k += 1
        while len(out) % 4:
            out += bytes(2)
        if base + len(out) > LIMIT:
            report['no_room'].append('telop block@%x' % bstart)
            continue
        d.extend(out)
        for ti, b in enumerate(s.blocks):
            if b == bstart:
                struct.pack_into('<I', d, s.tab + 4 * ti, base)
        report['telop_blocks'] += 1

    # ---- choice menus ----
    choice_rows = {r['off']: r for r in rows if r['kind'] == 'choice'}
    for i, t in enumerate(toks):
        if t[1] != 'op' or t[2] != 0x8008:
            continue
        hdr = list(t[3])
        j = i + 1
        texts = []
        cur_start = None
        ok = True
        while len(texts) < hdr[1]:
            tt = toks[j]
            if tt[1] == 'g' and cur_start is None:
                cur_start = tt[0]
            if tt[1] == 'op' and tt[2] == 0x8006:
                r = choice_rows.get(cur_start)
                if not r or not r['en']:
                    ok = False
                texts.append(r['en'] if r else None)
                cur_start = None
            j += 1
        jumps = [toks[j + k][3][0][1] for k in range(hdr[1])]
        end = toks[j + hdr[1] - 1][0] + 4
        if not ok:
            continue
        if not clear(t[0], t[0] + need(t[0])):
            report['skipped'].append('choice@%x' % t[0])
            continue
        enc = [encode_row(x, pack=False)[0] for x in texts]
        hdr[3] = max(len(e) for e in enc)
        menu = words([0x8008] + hdr)
        for e in enc:
            menu += words(e + [0x8006])
        table = b''.join(struct.pack('<I', tg) for tg in jumps)

        def make_menu(off, menu=menu, table=table):
            # the jump table must be 4-byte aligned: a null op in front of 8008 shifts it
            pad = words([0x8000]) if (off + len(menu)) % 4 else b''
            return pad + menu + table
        new = place(make_menu)
        if new is None:
            report['no_room'].append('choice@%x' % t[0])
            continue
        jb = jump(t[0], new)
        d[t[0]:t[0] + len(jb)] = jb
        release(t[0], end)
        report['choices'] += 1

    # ---- dialogue rows ----
    dlg = [r for r in rows if r['kind'] == 'dlg' and r['en'] and r['id'] not in telop_rows]
    handled = set()

    def last_tok(r):
        i = by_off[r['off']]
        while toks[i][0] + tok_len(toks[i]) < r['end']:
            i += 1
        return i

    for n_row, r in enumerate(dlg):
        if r['id'] in handled:
            continue
        i0 = by_off[r['off']]
        i1 = last_tok(r)
        text, visible = encode_row(r['en'])
        if visible > MAX_GLYPHS:
            report['too_many_glyphs'].append((r['id'], visible))
            continue
        # 1. in place: the packed English is no longer than the Japanese run (null ops pad the rest)
        room = r['end'] - r['off']
        if len(text) * 2 <= room and clear(r['off'], r['end']):
            d[r['off']:r['end']] = words(text + [0x8000] * (room // 2 - len(text)))
            report['in_place'] += 1
            continue
        pre = toks[i0 - 1] if i0 > 0 else None
        post = toks[i1 + 1] if i1 + 1 < len(toks) else None
        start, head = r['off'], []
        if pre and pre[1] == 'op' and pre[2] in SPEAKER_OPS and pre[0] + tok_len(pre) == r['off']:
            start, head = pre[0], [pre[2]] + list(pre[3])
        end, tail = r['end'], []
        if post and post[1] == 'op' and post[2] == 0x8003 and post[0] == r['end']:
            end, tail = r['end'] + 2, [0x8003]
        body = None
        if end - start < need(start) or not clear(start, start + need(start)):
            # 2. too short for a jump: move it together with the next row when only plain ops
            #    (no 32-bit operands) sit between the two, e.g. "We got" <item name op> "!"
            nxt = dlg[n_row + 1] if n_row + 1 < len(dlg) else None
            merged = False
            if nxt is not None and nxt['block'] == r['block']:
                j0 = by_off[nxt['off']]
                between = toks[i1 + 1:j0]
                if between and all(t[1] == 'op' and not any(isinstance(x, tuple) for x in t[3]) and (t[2] & 0xFFFF) != 0x8008
                                   for t in between):
                    j1 = last_tok(nxt)
                    text2, vis2 = encode_row(nxt['en'])
                    post2 = toks[j1 + 1] if j1 + 1 < len(toks) else None
                    end2, tail2 = nxt['end'], []
                    if post2 and post2[1] == 'op' and post2[2] == 0x8003 and post2[0] == nxt['end']:
                        end2, tail2 = nxt['end'] + 2, [0x8003]
                    if end2 - start >= need(start) and clear(start, end2) and visible + vis2 <= MAX_GLYPHS:
                        raw_between = bytes(s.d[between[0][0]:toks[j0][0]])
                        body = words(head + text) + raw_between + words(text2 + tail2)
                        end = end2
                        handled.add(nxt['id'])
                        merged = True
                        report['merged'] += 1
            if not merged:
                start, head, end, tail = r['off'], [], r['end'], []
                if end - start < need(start) or not clear(start, start + need(start)):
                    report['skipped'].append(r['id'])
                    continue
        if body is None:
            body = words(head + text + tail)
        new = place(lambda off, body=body, end=end: body + jump(off + len(body), end))
        if new is None:
            report['no_room'].append(r['id'])
            continue
        jb = jump(start, new)
        d[start:start + len(jb)] = jb
        release(start, end)
        report['moved'] += 1
    report['size'] = len(d)
    assert len(d) <= LIMIT
    return bytes(d), report


def verify(path, out):
    """The rebuilt file must keep every original token position that is still reachable:
    walk it from each block start following jumps, and check that only known tokens appear."""
    import scene as sc
    d = out
    hdr = struct.unpack_from('<12I', d, 0)
    s0 = sc.Scene(path)
    seen = set()
    todo = [b for b in s0.blocks if b]
    bad = []
    steps = 0
    while todo:
        p = todo.pop()
        while p not in seen and p + 2 <= len(d):
            seen.add(p)
            steps += 1
            w = struct.unpack_from('<H', d, p)[0]
            if w < 0x8000:                      # glyph or packed pair
                if 0x52B <= w < 0x1000:
                    bad.append((p, w))
                    break
                p += 2
                continue
            if w == 0xFFFF:
                p += 2
                continue
            if w == 0x8008:
                h = struct.unpack_from('<4H', d, p + 2)
                q = p + 10
                n = 0
                while n < h[1]:
                    if struct.unpack_from('<H', d, q)[0] == 0x8006:
                        n += 1
                    q += 2
                for k in range(h[1]):
                    todo.append(struct.unpack_from('<I', d, q + 4 * k)[0])
                break
            if w not in sc.ARGS:
                bad.append((p, w))
                break
            q = p + 2
            nxt = None
            for c in sc.ARGS[w]:
                if c == 'w':
                    q += 2
                else:
                    v = struct.unpack_from('<I', d, q)[0]
                    if c == 'O':
                        todo.append(v)
                        if w == 0x8016:
                            nxt = 'stop'
                    q += 4
            if nxt == 'stop':
                break
            p = q
    return steps, bad


if __name__ == '__main__':
    import json
    for sc_name in sys.argv[1:]:
        rows = json.load(open('work/translation/en/scenes/%s.json' % sc_name, encoding='utf-8'))
        path = 'work/source/winbin/%s.bin' % sc_name[1:]
        out, rep = build_scene(path, rows)
        steps, bad = verify(path, out)
        print(sc_name, os.path.getsize(path), '->', rep['size'], 'of', LIMIT,
              {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items() if k != 'size'},
              'walk', steps, 'bad', bad[:3])
