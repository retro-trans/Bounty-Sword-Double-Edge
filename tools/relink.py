"""Rebuild an event file's script banks with the English text (ported from the Bounty Sword First
relinker; see docs/VWF.md).

Differences from the sister game that shape this version:
* banks are not always contiguous and some have no header slot (tools/scene.py finds them), so
  every bank keeps its table where it is and its stream is laid out again inside its own region
  [stream start, stream end). What does not fit continues after the end of the file, reached by a
  jump (0x8016) placed before a speaker op or a block start. The file may not exceed LIMIT.
* jump operands are absolute addresses (kind 'O': file offset + scene.BASE) or file offsets
  (kind 'F'); both are remapped.
* the per-file word dictionary goes after the end of the file and its file offset is stored in
  header slot 17 (offset 0x44; zero in every original file), where the fetch hook reads it.

Text the interpreter prints is packed: token 0x1000 + a*128 + b = two glyphs of the pair table,
token 0x5000 + i = dictionary word i. Choice-menu text and blocks that start with unquoted text
(narration; may be read by code that does not expand tokens) stay plain glyph tokens.

    build_scene(path, rows) -> (bytes, report, info);  fit(...) drops rows from the end if over LIMIT
    python tools/relink.py K000 S012 ...     report only
"""
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as sc
from scene import check, ARGS, BASE
from hooks import pack_pairs, PAIR_CHARS, PAIR_INDEX
import enfont

NULL = 0x8000
JUMP = 0x8016
PAIR_BASE = 0x1000
DICT_BASE = 0x5000
DICT_MAX = 0x3000
LIMIT = 0x9408                 # overlay 1 ends at 0x80115C54; the file loads at 0x8010C84C
DICT_SLOT = 17                 # header slot holding the dictionary's file offset
MAX_GLYPHS = 150               # glyph pool has 200 slots, shared with name boxes etc.
SPEAKER_OPS = {0x8002, 0x804F, 0x8064, 0x8061, 0x8068, 0x8033, 0x8024}
INLINE_OPS = {0x8005, 0x8009, 0x800A, 0x8019, 0x802D, 0x8031, 0x8057, 0x800C}
TAG = re.compile(r'\{([^}]*)\}')
_CHUNK = re.compile(r"[A-Za-z']+ ?|\.\.\. ?|.", re.S)
SPACE = enfont.SPACE
OPEN_QUOTES = {11, 13}         # glyphs that open a dialogue line in the source
ZERO4 = bytes(4)


def encode_row(text, pack=True):
    """Row text with tags -> (tokens, visible glyph count)."""
    out = []
    visible = 0

    def run(s):
        nonlocal visible
        codes = enfont.encode(s)
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
        elif t == '800c':
            out.append(0x800C)
        elif t == 'var':
            out.append(0x8057)
            visible += 6
        else:
            raise ValueError('unknown tag {%s}' % t)
        pos = m.end()
    out += run(text[pos:])
    return out, visible


def build_dictionary(texts):
    """Words (with their trailing space) worth one token each."""
    freq = collections.Counter()
    for t in texts:
        for part in TAG.split(t)[::2]:
            for w in _CHUNK.findall(part):
                if len(w) >= 3:
                    freq[w] += 1
    # a word of n letters costs about n/2 tokens packed; as a dictionary token it costs 1,
    # plus n + 4 bytes once for the entry
    gain = {w: c * (len(w) - 2) - (len(w) + 4) for w, c in freq.items()}
    words = sorted((w for w in gain if gain[w] > 0), key=lambda w: (-gain[w], w))
    return words[:DICT_MAX]


def dictionary_blob(words):
    """u16 offsets from the blob start, then entries [n][pair-table indices][FF]."""
    if not words:
        return b''
    table = bytearray()
    body = bytearray()
    base = 2 * len(words)
    for w in words:
        table += struct.pack('<H', base + len(body))
        idx = [PAIR_INDEX[enfont.ENC[c]] for c in w]
        body += bytes([len(idx)] + idx + [0xFF])
    assert base + len(body) < 0x10000
    return bytes(table + body)


def encode_text(text, index):
    """Dialogue: tags -> ops, dictionary words -> one token, the rest in pairs. -> (tokens, visible)"""
    out = []
    visible = 0
    run = []

    def flush():
        if run:
            out.extend(pack_pairs(run))
            del run[:]

    pos = 0
    pieces = []
    for m in TAG.finditer(text):
        pieces.append(('t', text[pos:m.start()]))
        pieces.append(('g', m.group(0)))
        pos = m.end()
    pieces.append(('t', text[pos:]))
    for kind, part in pieces:
        if kind == 'g':
            flush()
            ops, vis = encode_row(part, pack=False)
            out.extend(ops)
            visible += vis
            continue
        for w in _CHUNK.findall(part):
            visible += sum(1 for c in w if c != ' ')
            if w in index:
                flush()
                out.append(DICT_BASE + index[w])
            else:
                run.extend(enfont.encode(w))
    flush()
    return out, visible


def decode_tokens(tokens, words):
    """What the patched interpreter prints for these tokens (mirror of the fetch hook)."""
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        w = tokens[i]
        i += 1
        if w < PAIR_BASE:
            out.append(w)
        elif w < DICT_BASE:
            v = w - PAIR_BASE
            out += [enfont.ENC[PAIR_CHARS[v >> 7]], enfont.ENC[PAIR_CHARS[v & 0x7F]]]
        elif w < 0x8000:
            out += enfont.encode(words[w - DICT_BASE])
        else:
            out.append(w)
            k = len(ARGS.get(w, ''))
            out += tokens[i:i + k]
            i += k
    return out


def W(ws):
    return b''.join(struct.pack('<H', w) for w in ws)


def tok_len(t):
    if t[2] == (JUMP | 0x10000):
        return 4
    return 2 + sum(4 if isinstance(a, tuple) else 2 for a in t[3])


class Item:
    __slots__ = ('old', 'data', 'align32', 'ops32', 'split', 'pos')

    def __init__(self, old, data, align32=None, ops32=(), split=False):
        self.old = old
        self.data = bytes(data)
        self.align32 = align32      # byte index inside data that must be 4-aligned
        self.ops32 = list(ops32)    # [(byte index, old target file offset, kind 'O'|'F')]
        self.split = split          # the stream may be cut (overflow jump) right before this item
        self.pos = None


def regions(s):
    """Per bank: (stream start, real stream end)."""
    return [(st, s.stream_end.get(en, en)) for slot, tab, st, en in s.sections]


def build_scene(path, rows, drop_rows=(), use_dict=True):
    s, toks, bad = check(path)
    assert not bad, bad
    d = s.d
    report = {'rows': 0, 'choices': 0, 'too_many_glyphs': [], 'target_inside_text': [], 'overflow': 0,
              'dropped': len(drop_rows)}
    by_off = {t[0]: i for i, t in enumerate(toks)}
    regs = regions(s)

    targets = set(b for b in s.blocks if b)
    for t in toks:
        for a in t[3]:
            if isinstance(a, tuple) and a[0] in 'OF':
                targets.add(a[1])
    row_at = {r['off']: r for r in rows if r['id'] not in drop_rows}
    block_set = set(b for b in s.blocks if b)
    starts = sorted(block_set)
    ends = sorted(e for _, e in regs)

    # narration blocks: a block that begins with text that is not an opening quote
    plain_range = []
    for b in starts:
        if b not in by_off:
            continue
        t0 = toks[by_off[b]]
        if t0[1] == 'g' and t0[2] not in OPEN_QUOTES:
            end = min([e for e in ends + starts if e > b] or [len(d)])
            plain_range.append((b, end))

    def is_plain(off):
        return any(a <= off < b for a, b in plain_range)

    packed_texts = [r['en'] for r in rows if r['kind'] == 'dlg' and r['en'] and r['id'] not in drop_rows
                    and not is_plain(r['off'])]
    words = build_dictionary(packed_texts) if use_dict else []
    windex = {w: i for i, w in enumerate(words)}
    report['dict_words'] = len(words)

    banks = []
    n_tok = len(toks)
    for (st, en) in regs:
        items = []
        i = by_off.get(st, n_tok)
        while i < n_tok and st <= toks[i][0] < en:       # tokens are in bank order, not file order
            off, kind, val, args = toks[i]
            is_block = off in block_set
            if kind == 'op' and val == 0x8008:                      # choice menu: atomic
                hdr = list(args)
                j = i + 1
                texts = []
                cur = []
                cur_start = None
                while len(texts) < hdr[1]:
                    tt = toks[j]
                    if tt[1] == 'op' and tt[2] == 0x8006:
                        texts.append((cur_start, cur))
                        cur, cur_start = [], None
                    else:
                        if cur_start is None:
                            cur_start = tt[0]
                        cur.append(tt[2])
                        cur.extend(tt[3])
                    j += 1
                tbl = [toks[j + q][3][0][1] for q in range(hdr[1])]
                enc = []
                translated = False
                for cs, ws in texts:
                    r = row_at.get(cs)
                    if r is not None and r['kind'] == 'choice' and r['en']:
                        enc.append(encode_row(r['en'], pack=False)[0])
                        translated = True
                    else:
                        enc.append(list(ws))
                if translated:
                    report['choices'] += 1
                body = W([0x8008] + hdr)
                for e in enc:
                    body += W(e + [0x8006])
                tpos = len(body)
                body += ZERO4 * len(tbl)
                items.append(Item(off, body, align32=tpos,
                                  ops32=[(tpos + 4 * q, tg, 'F') for q, tg in enumerate(tbl)], split=is_block))
                i = j + hdr[1]
                continue
            if kind == 'g' and off in row_at and row_at[off]['kind'] == 'dlg' and row_at[off]['en']:
                r = row_at[off]
                if [t for t in targets if r['off'] < t < r['end']]:
                    report['target_inside_text'].append(r['id'])
                else:
                    if is_plain(off):
                        ws, vis = encode_row(r['en'], pack=False)
                    else:
                        ws, vis = encode_text(r['en'], windex)
                        assert decode_tokens(ws, words) == encode_row(r['en'], pack=False)[0], r['id']
                    if vis > MAX_GLYPHS:
                        report['too_many_glyphs'].append((r['id'], vis))
                    else:
                        items.append(Item(off, W(ws), split=is_block))
                        report['rows'] += 1
                        while i < n_tok and toks[i][0] < r['end']:
                            i += 1
                        continue
            raw = d[off:off + tok_len(toks[i])]
            if kind == 'op' and val == NULL and off not in targets:
                items.append(Item(off, b''))                     # dropped pad: keeps the offset in the map
                i += 1
                continue
            if kind == 'op' and any(isinstance(a, tuple) for a in args):
                q = 2
                first = None
                ops32 = []
                for c, a in zip(ARGS[val], args):
                    if c == 'w':
                        q += 2
                    else:
                        if first is None:
                            first = q
                        if c in 'OF':
                            ops32.append((q, a[1], c))
                        q += 4
                items.append(Item(off, raw, align32=first, ops32=ops32, split=is_block))
                i += 1
                continue
            items.append(Item(off, raw, split=is_block or (kind == 'op' and val in SPEAKER_OPS and not is_plain(off))))
            i += 1
        banks.append(items)

    # ---- layout ----
    out = bytearray(d)
    for st, en in regs:
        out[st:en] = bytes(en - st)
    overflow_base = (len(d) + 3) & ~3
    over = bytearray()
    mapping = {}
    jumps = []                      # (file position of operand, new target file offset)
    segs = [[] for _ in banks]
    extra_jumps = set()
    used = []

    def group_size(items, q):
        n = 0
        j = q
        while True:
            n += len(items[j].data) + (2 if items[j].align32 is not None else 0)
            j += 1
            if j >= len(items) or items[j].split:
                return n

    for k, items in enumerate(banks):
        st, en = regs[k]
        state = {'pos': st, 'over': False}
        seg_start = st

        def emit(b):
            if state['over']:
                over.extend(b)
            else:
                out[state['pos']:state['pos'] + len(b)] = b
            state['pos'] += len(b)

        # bytes still to place from item q on (worst case: every aligned item needs a 2-byte pad)
        rest = [0] * (len(items) + 1)
        for q in range(len(items) - 1, -1, -1):
            rest[q] = rest[q + 1] + len(items[q].data) + (2 if items[q].align32 is not None else 0)
        for q, it in enumerate(items):
            if it.split and not state['over'] and state['pos'] + rest[q] > en                     and state['pos'] + group_size(items, q) + 12 > en:
                if (state['pos'] + 2) % 4:
                    emit(W([NULL]))
                jp = state['pos']
                emit(W([JUMP]) + ZERO4)
                segs[k].append((seg_start, state['pos']))
                used.append(state['pos'] - st)
                state['over'] = True
                state['pos'] = overflow_base + len(over)
                seg_start = state['pos']
                jumps.append((jp + 2, state['pos']))
                extra_jumps.add(state['pos'])
                report['overflow'] += 1
            if not it.data:
                mapping[it.old] = None
                continue
            if it.align32 is not None and (state['pos'] + it.align32) % 4:
                emit(W([NULL]))
            it.pos = state['pos']
            mapping[it.old] = state['pos']
            emit(it.data)
        pos = state['pos']
        assert state['over'] or pos <= en, (hex(pos), hex(en))
        segs[k].append((seg_start, pos))
        if not state['over']:
            used.append(pos - st)
        else:
            while len(over) % 4:
                over.extend(W([NULL]))
        # jumps to the end of the bank, dropped pads -> next real position
        mapping.setdefault(s.sections[k][3], pos)
        mapping.setdefault(en, pos)
        nxt = pos
        for it in reversed(items):
            if it.data:
                nxt = it.pos
            elif mapping.get(it.old) is None:
                mapping[it.old] = nxt

    if over:
        out.extend(bytes(overflow_base - len(out)))
        out.extend(over)
    dict_off = 0
    blob = dictionary_blob(words)
    if blob:
        while len(out) % 4:
            out.append(0)
        dict_off = len(out)
        out.extend(blob)
    while len(out) % 4:
        out.append(0)
    if len(out) != len(d):
        # header slot 1 points at the last four bytes of the file, which the game writes to at run
        # time (seen in RAM: the tail of a dictionary placed there was overwritten). Keep a spare word.
        out.extend(ZERO4)
    report['dict_bytes'] = len(blob)

    def in_banks(tg):
        return any(st <= tg <= s.sections[k][3] for k, (st, en) in enumerate(regs))

    def remap(tg):
        if mapping.get(tg) is not None:
            return mapping[tg]
        if not in_banks(tg):
            return tg                                # points outside the banks: unchanged
        raise KeyError('unmapped target %x' % tg)

    def put32(p, v):
        assert p % 4 == 0, hex(p)
        struct.pack_into('<I', out, p, v)

    for items in banks:
        for it in items:
            for q, tg, kind in it.ops32:
                put32(it.pos + q, remap(tg) + (BASE if kind == 'O' else 0))
    for p, v in jumps:
        put32(p, v + BASE)
    for pos_, v in zip(s.block_pos, s.blocks):
        struct.pack_into('<I', out, pos_, remap(v) if v else 0)
    assert s.hdr[DICT_SLOT] == 0
    struct.pack_into('<I', out, DICT_SLOT * 4, dict_off)
    if len(out) != len(d) and s.hdr[1] == len(d) - 4:
        struct.pack_into('<I', out, 4, len(out) - 4)       # slot 1 = offset of the last word

    report['size'] = len(out)
    report['region_used'] = sum(used)
    report['region'] = sum(en - st for st, en in regs)
    report['over_limit'] = len(out) > LIMIT
    return bytes(out), report, dict(mapping=mapping, s=s, toks=toks, segs=segs, extra_jumps=extra_jumps,
                                    dict_off=dict_off, words=words)


def fit(path, rows):
    """Build; if the file is over LIMIT, leave rows untranslated from the end until it fits."""
    drop = []
    cand = [r['id'] for r in rows if r['kind'] == 'dlg' and r['en']]
    while True:
        out, rep, info = build_scene(path, rows, set(drop))
        if not rep['over_limit']:
            rep['left_japanese'] = list(drop)
            return out, rep, info
        drop += cand[-20:]
        del cand[-20:]


def linear_ops(d, ranges, mapping=None):
    """Tokenize script bytes; -> (ordered structural ops, inline-op counts, problems). Jump targets are
    file offsets; with `mapping` the ORIGINAL's targets are translated to the new offsets."""
    ops = []
    inline = collections.Counter()
    bad = []

    def mp(x):
        if mapping is not None and mapping.get(x) is not None:
            return mapping[x]
        return x

    for a, b in ranges:
        p = a
        while p < b:
            w = struct.unpack_from('<H', d, p)[0]
            if w < 0x8000:
                p += 2
                continue
            if w == 0x8008:
                h = struct.unpack_from('<4H', d, p + 2)
                q = p + 10
                n = 0
                while n < h[1]:
                    v = struct.unpack_from('<H', d, q)[0]
                    if v == 0x8006:
                        n += 1
                    elif v in (0x8009, 0x800A):
                        inline[v] += 1
                        q += 2
                    q += 2
                if q % 4:
                    bad.append(('choice table not aligned', p, q))
                tg = [mp(struct.unpack_from('<I', d, q + 4 * e)[0]) for e in range(h[1])]
                ops.append((0x8008, h[0], h[1], h[2]) + tuple(tg))
                p = q + 4 * h[1]
                continue
            if w not in ARGS:
                bad.append(('unknown op', p, w))
                p += 2
                continue
            q = p + 2
            key = [w]
            for c in ARGS[w]:
                if c == 'w':
                    key.append(struct.unpack_from('<H', d, q)[0])
                    q += 2
                else:
                    if q % 4:
                        bad.append(('operand not aligned', p, w))
                    v = struct.unpack_from('<I', d, q)[0]
                    if c == 'O':
                        v = mp(v - BASE)
                    elif c == 'F':
                        v = mp(v)
                    key.append(v)
                    q += 4
            if w == NULL:
                pass
            elif w in INLINE_OPS:
                inline[w] += 1
            else:
                ops.append(tuple(key))
            p = q
    return ops, inline, bad


def verify(path, out, info):
    """Per bank: same structural ops in the same order with the same arguments and remapped jumps;
    block tables are the remapped originals; operands aligned; no unknown op; nothing outside the
    bank regions changed."""
    s = info['s']
    m = {k: v for k, v in info['mapping'].items() if isinstance(k, int)}
    problems = []
    regs = regions(s)
    for k, (st, en) in enumerate(regs):
        a, ia, bad_a = linear_ops(s.d, [(st, en)], m)
        b, ib, bad_b = linear_ops(out, info['segs'][k])
        b = [x for x in b if not (x[0] == JUMP and x[1] in info['extra_jumps'])]
        if bad_b:
            problems.append(('bank %d' % k, bad_b[:3]))
        if a != b:
            n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            problems.append(('bank %d ops differ at #%d of %d/%d' % (k, n, len(a), len(b)), a[n:n + 2], b[n:n + 2]))
        for op in INLINE_OPS - {0x8005}:
            if ia[op] != ib[op]:
                problems.append(('bank %d inline op %04x count %d -> %d' % (k, op, ia[op], ib[op]),))
    for pos_, v in zip(s.block_pos, s.blocks):
        nv = struct.unpack_from('<I', out, pos_)[0]
        if nv != (m[v] if v else 0):
            problems.append(('table entry at %x' % pos_, v, nv))
            break
    if struct.unpack_from('<I', out, DICT_SLOT * 4)[0] != info['dict_off']:
        problems.append(('dictionary pointer',))
    keep = bytearray(s.d)
    new = bytearray(out[:len(s.d)])
    for buf in (keep, new):
        for st, en in regs:
            buf[st:en] = bytes(en - st)
        for pos_ in s.block_pos:
            buf[pos_:pos_ + 4] = ZERO4
        buf[4:8] = ZERO4
        buf[DICT_SLOT * 4:DICT_SLOT * 4 + 4] = ZERO4
    if keep != new:
        problems.append(('bytes outside the banks changed',))
    return problems


if __name__ == '__main__':
    for name in sys.argv[1:]:
        rows = json.load(open('work/translation/en/scenes/%s.json' % name, encoding='utf-8'))
        path = 'work/source/%s/%s.bin' % ('kive' if name[0] == 'K' else 'sive', name[1:])
        out, rep, info = fit(path, rows)
        problems = verify(path, out, info)
        show = {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}
        print(name, os.path.getsize(path), '->', show, 'verify:', problems if problems else 'ok')
