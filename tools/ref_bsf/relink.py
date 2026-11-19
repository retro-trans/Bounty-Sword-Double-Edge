"""Rebuild a scene file's script banks linearly with the English text (replaces the jump /
hole scheme of tools/insert_scenes.py, which fragments and cannot fit the largest scenes).

A scene file starts with a header of 12 u32 offsets; the three script banks (header slots
3, 6, 7) lie contiguously after it, before every other section. The game reads the bank
positions from the loaded header and every script offset is file-relative, so the whole
bank region can be laid out again:

    [table 3][table 6][table 7][stream 3][stream 6][stream 7]   (header slots 6, 7 updated)

* every original token is emitted in order; translated text runs are replaced;
* an old-offset -> new-offset map covers every token start; block-table entries and every
  32-bit jump operand are rewritten through it;
* 32-bit operands are kept 4-byte aligned with null ops (0x8000) as the original does;
  original null ops that nothing points at are dropped;
* dialogue the interpreter prints is packed two letters per token; choice-menu text and
  telop blocks (read by code that does not expand pairs) are plain glyph tokens;
* if the region is too small, the rest continues after the end of the file, reached by a
  jump placed before a speaker op or a block start; the file may not exceed LIMIT.

    build_scene(path, rows) -> (bytes, report)
    python tools/relink.py S033 S089 ...     report only
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as sc
from scene import check, ARGS
from hooks import pack_pairs, PAIR_CHARS
import enfont
from insert_scenes import encode_row, telop_lines, tok_len, SPEAKER_OPS, MAX_GLYPHS, LIMIT

NULL = 0x8000
PAIR_MAX = 0x7FFF        # 0x1000..0x4FFF pairs, 0x5000..0x7FFF dictionary words
DICT_BASE = 0x5000
DICT_MAX = 0x3000
PAIR_INDEX = {enfont.ENC[c]: i for i, c in enumerate(PAIR_CHARS)}
import re
import collections
_TAG = re.compile(r'\{[^}]*\}')
_CHUNK = re.compile(r"[A-Za-z']+ ?|\.\.\. ?|.", re.S)


def build_dictionary(texts):
    """Words (with their trailing space) worth one token each: uses * (len - 2) bytes saved
    against len + 4 bytes for the entry. -> list of strings, best first."""
    freq = collections.Counter()
    for t in texts:
        for part in _TAG.split(t):
            for w in _CHUNK.findall(part):
                if len(w) >= 3:
                    freq[w] += 1
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
    """Dialogue the interpreter prints: tags -> ops, words in the dictionary -> one token,
    the rest packed in pairs. -> (tokens, visible glyph count)"""
    out = []
    visible = 0
    run = []

    def flush():
        if run:
            out.extend(pack_pairs(run))
            del run[:]

    pos = 0
    pieces = []
    for m in _TAG.finditer(text):
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
    """What the patched interpreter prints for these tokens (mirror of tools/hooks.py fetch)."""
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        w = tokens[i]
        i += 1
        if w < 0x1000:
            out.append(w)
        elif w < DICT_BASE:
            v = w - 0x1000
            out += [enfont.ENC[PAIR_CHARS[v >> 7]], enfont.ENC[PAIR_CHARS[v & 0x7F]]]
        elif w < 0x8000:
            out += enfont.encode(words[w - DICT_BASE])
        else:
            out.append(w)
            k = len(ARGS.get(w, ''))
            out += tokens[i:i + k]          # inline ops here only take word arguments
            i += k
    return out


def W(ws):
    return b''.join(struct.pack('<H', w) for w in ws)


class Item:
    """One emitted piece. old = original offset it stands for (or None)."""
    __slots__ = ('old', 'data', 'align32', 'ops32', 'split', 'keep_mod', 'pos', 'group')

    def __init__(self, old, data, align32=None, ops32=(), split=False, keep_mod=None):
        self.old = old
        self.data = bytes(data)
        self.align32 = align32      # byte index inside data that must be 4-aligned (first 32-bit operand)
        self.ops32 = list(ops32)    # [(byte index, old target)] operands to remap
        self.split = split          # the stream may be cut (overflow jump) right before this item
        self.keep_mod = keep_mod    # required (position % 4), for raw data structures
        self.pos = None


def build_scene(path, rows, drop_rows=(), use_dict=True):
    s, toks, bad = check(path)
    assert not bad, bad
    d = s.d
    report = {'rows': 0, 'choices': 0, 'telop_blocks': 0, 'too_many_glyphs': [], 'telop_wide': [],
              'target_inside_text': [], 'overflow': 0, 'dropped': len(drop_rows)}
    by_off = {t[0]: i for i, t in enumerate(toks)}
    region_start = s.sections[0][1]
    region_end = max(s.ends)
    assert [x[1] for x in s.sections] == sorted(x[1] for x in s.sections)

    # ---- targets ----
    targets = set(b for b in s.blocks if b)
    for t in toks:
        for a in t[3]:
            if isinstance(a, tuple) and a[0] == 'O':
                targets.add(a[1])
    # self-pointers inside raw data (bank 7): a data word + zero word forming a u32 that is a token start
    ptr_at = {}
    for i, t in enumerate(toks[:-1]):
        if t[1] == 'd' and t[0] % 4 == 0 and toks[i + 1][1] == 'g' and toks[i + 1][2] == 0 and toks[i + 1][0] == t[0] + 2:
            if t[2] in by_off and region_start <= t[2] < region_end:
                ptr_at[t[0]] = t[2]
                targets.add(t[2])

    row_at = {r['off']: r for r in rows if r['id'] not in drop_rows}
    starts = sorted(set(b for b in s.blocks if b))
    block_set = set(starts)

    def sect_of(off):
        for k, (slot, tab, st, en) in enumerate(s.sections):
            if st <= off < en:
                return k
        raise ValueError(hex(off))

    # telop blocks: begin with unquoted text
    telop_range = []
    for bi, b in enumerate(starts):
        t0 = toks[by_off[b]]
        scene_bank = s.sections[0][0] == 3 and s.sections[0][2] <= b < s.sections[0][3]
        if scene_bank and t0[1] == 'g' and t0[2] != 0x05:
            end = min(e for e in sorted(s.ends) + starts if e > b)
            telop_range.append((b, end))

    def in_telop(off):
        return any(a <= off < b for a, b in telop_range)

    # ---- dictionary from every row the interpreter will print packed ----
    packed_texts = [r['en'] for r in rows if r['kind'] == 'dlg' and r['en'] and r['id'] not in drop_rows and not in_telop(r['off'])]
    words = build_dictionary(packed_texts) if use_dict else []
    windex = {w: i for i, w in enumerate(words)}
    report['dict_words'] = len(words)

    # ---- items per bank ----
    banks = []
    for k, (slot, tab, st, en) in enumerate(s.sections):
        items = []
        i = by_off[st]
        n_tok = len(toks)
        while i < n_tok and toks[i][0] < en:
            off, kind, val, args = toks[i]
            op = val & 0xFFFF
            is_block = off in block_set
            # choice menu: atomic
            if kind == 'op' and val == 0x8008:
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
                    hdr[3] = max(hdr[3], max(len(e) for e in enc))
                    report['choices'] += 1
                body = W([0x8008] + hdr)
                for e in enc:
                    body += W(e + [0x8006])
                tpos = len(body)
                body += b'\x00' * (4 * len(tbl))
                items.append(Item(off, body, align32=tpos, ops32=[(tpos + 4 * q, tg) for q, tg in enumerate(tbl)], split=is_block))
                i = j + hdr[1]
                continue
            # translated text run
            if kind == 'g' and off in row_at and row_at[off]['kind'] == 'dlg' and row_at[off]['en']:
                r = row_at[off]
                inside = [t for t in targets if r['off'] < t < r['end']]
                if inside:
                    report['target_inside_text'].append(r['id'])
                else:
                    if in_telop(off):
                        lines, wide = telop_lines(r['jp'], r['en'])
                        for x in wide:
                            report['telop_wide'].append((r['id'],) + x)
                        ws = []
                        for q, codes in enumerate(lines):
                            if q:
                                ws.append(0x8005)
                            ws += codes
                        vis = 0
                    else:
                        ws, vis = encode_text(r['en'], windex)
                        plain = encode_row(r['en'], pack=False)[0]
                        assert decode_tokens(ws, words) == plain, r['id']       # round trip
                    if vis > MAX_GLYPHS:
                        report['too_many_glyphs'].append((r['id'], vis))
                    else:
                        items.append(Item(off, W(ws), split=is_block))
                        report['rows'] += 1
                        while i < n_tok and toks[i][0] < r['end']:
                            i += 1
                        continue
            raw = d[off:off + tok_len(toks[i])]
            if off in ptr_at:
                # u32 self-pointer inside raw data: this word + the next (zero) word
                items.append(Item(off, b'\x00' * 4, align32=0, ops32=[(0, ptr_at[off])], keep_mod=0))
                i += 2
                continue
            if kind == 'op' and op == NULL and off not in targets:
                items.append(Item(off, b''))            # dropped pad: keeps the offset in the map
                i += 1
                continue
            if kind == 'op' and any(isinstance(a, tuple) for a in args):
                q = 2
                first = None
                ops32 = []
                for c, a in zip(ARGS[op], args):
                    if c == 'w':
                        q += 2
                    else:
                        if first is None:
                            first = q
                        if c == 'O':
                            ops32.append((q, a[1]))
                        q += 4
                items.append(Item(off, raw, align32=first, ops32=ops32, split=is_block))
                i += 1
                continue
            it = Item(off, raw, split=is_block or (kind == 'op' and op in SPEAKER_OPS and not in_telop(off)))
            if kind == 'd':
                it.keep_mod = off % 4
            items.append(it)
            i += 1
        banks.append(items)

    # raw data structures (a 'd' word present): keep the alignment of the whole run that leads to it
    for items in banks:
        for q, it in enumerate(items):
            if it.keep_mod is not None and it.align32 is None:
                j = q
                while j > 0 and not items[j - 1].split and items[j - 1].old is not None and \
                        toks[by_off[items[j - 1].old]][1] in ('g', 'd') and items[j - 1].keep_mod is None:
                    j -= 1
                    items[j].keep_mod = items[j].old % 4

    # ---- layout ----
    tabs = [(tab, (st - tab)) for (slot, tab, st, en) in s.sections]
    out = bytearray(d)
    pos = region_start
    new_tab = []
    for tab, size in tabs:
        new_tab.append(pos)
        pos += size
    out[region_start:region_end] = b'\x00' * (region_end - region_start)
    overflow_base = (len(d) + 3) & ~3
    over = bytearray()
    in_over = [False]
    mapping = {}
    jumps = []                      # (absolute position of operand, absolute new target)
    segs = [[] for _ in banks]      # per bank: [start, end) pieces of its new stream
    extra_jumps = set()             # targets of the overflow jumps this builder added

    def emit(b):
        nonlocal pos
        if in_over[0]:
            over.extend(b)
        else:
            out[pos:pos + len(b)] = b
        pos += len(b)

    def group_size(items, q):
        n = 0
        j = q
        while True:
            n += len(items[j].data) + 2
            j += 1
            if j >= len(items) or items[j].split:
                return n

    for k, items in enumerate(banks):
        seg_start = pos
        for q, it in enumerate(items):
            if it.split and not in_over[0] and pos + group_size(items, q) + 16 > region_end:
                # continue after the end of the file
                if (pos + 2) % 4:
                    emit(W([NULL]))
                jp = pos
                emit(W([0x8016]) + b'\x00\x00\x00\x00')
                segs[k].append((seg_start, pos))
                in_over[0] = True
                pos = overflow_base
                seg_start = pos
                jumps.append((jp + 2, pos))
                extra_jumps.add(pos)
                report['overflow'] = 1
            if not it.data:
                mapping[it.old] = None          # resolved below to the next emitted position
                continue
            need_pad = False
            if it.align32 is not None and (pos + it.align32) % 4:
                need_pad = True
            if it.keep_mod is not None and it.align32 is None and pos % 4 != it.keep_mod:
                need_pad = True
            if need_pad:
                emit(W([NULL]))
            it.pos = pos
            if it.old is not None:
                mapping[it.old] = pos
            emit(it.data)
        segs[k].append((seg_start, pos))
        mapping[s.sections[k][3]] = pos          # jumps to the end of the bank
        mapping.setdefault(('end', k), pos)
    assert in_over[0] or pos <= region_end, (pos, region_end)

    # dropped pads map to the next real position
    order = []
    for k, items in enumerate(banks):
        nxt = mapping[s.sections[k][3]]
        for it in reversed(items):
            if it.data:
                nxt = it.pos
            elif mapping.get(it.old) is None:
                mapping[it.old] = nxt

    if in_over[0]:
        if len(out) < overflow_base:
            out.extend(b'\x00' * (overflow_base - len(out)))
        out.extend(over)
        while len(out) % 4:
            out.append(0)

    dict_off = 0
    blob = dictionary_blob(words)
    if blob:
        slack_at = (pos + 3) & ~3
        if not in_over[0] and slack_at + len(blob) <= region_end:
            dict_off = slack_at                          # inside the bank region's free tail
            out[dict_off:dict_off + len(blob)] = blob
            report['dict_in_region'] = 1
        else:
            while len(out) % 4:
                out.append(0)
            dict_off = len(out)
            out.extend(blob)
            while len(out) % 4:
                out.append(0)
    report['dict_bytes'] = len(blob)

    def put32(p, v):
        assert p % 4 == 0, hex(p)
        struct.pack_into('<I', out, p, v)

    def remap(tg):
        if tg in mapping and mapping[tg] is not None:
            return mapping[tg]
        if not (region_start <= tg < region_end):
            return tg                            # points outside the banks: unchanged
        raise KeyError('unmapped target %x' % tg)

    for items in banks:
        for it in items:
            for q, tg in it.ops32:
                put32(it.pos + q, remap(tg))
    for p, v in jumps:
        put32(p, v)
    # tables and header
    tpos = region_start
    bi = 0
    for k, (tab, size) in enumerate(tabs):
        for e in range(size // 4):
            v = s.blocks[bi]
            bi += 1
            struct.pack_into('<I', out, new_tab[k] + 4 * e, remap(v) if v else 0)
        # entry 0 is never a block (it is 0 in every original table): it holds the dictionary offset
        assert s.blocks[bi - size // 4] == 0, 'table entry 0 is in use'
        struct.pack_into('<I', out, new_tab[k], dict_off)
    for k, (slot, tab, st, en) in enumerate(s.sections):
        struct.pack_into('<I', out, slot * 4, new_tab[k])

    report['size'] = len(out)
    report['region_used'] = (region_end if in_over[0] else pos) - region_start
    report['region'] = region_end - region_start
    report['over_limit'] = len(out) > LIMIT
    return bytes(out), report, dict(mapping=mapping, new_tab=new_tab, s=s, toks=toks, segs=segs, extra_jumps=extra_jumps,
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


INLINE_OPS = {0x8005, 0x8009, 0x800A, 0x8019, 0x802D, 0x8031, 0x8057}


def linear_ops(d, ranges, mapping=None):
    """Tokenize script bytes in the given ranges; return (ordered structural ops, inline-op counts, problems).
    A structural op is (op, word args..., jump targets...). With `mapping`, jump targets of the
    ORIGINAL are translated to new offsets so both sides can be compared directly."""
    import collections
    ops = []
    inline = collections.Counter()
    bad = []
    for a, b in ranges:
        p = a
        while p < b:
            w = struct.unpack_from('<H', d, p)[0]
            if w < 0x8000:
                if w > PAIR_MAX:
                    bad.append(('unknown token', p, w))
                p += 2
                continue
            if w == 0xFFFF:
                ops.append((w,))
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
                if q % 4:
                    bad.append(('choice table not aligned', p, q))
                tg = [struct.unpack_from('<I', d, q + 4 * e)[0] for e in range(h[1])]
                if mapping is not None:
                    tg = [mapping.get(x, x) for x in tg]
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
                    if c == 'O' and mapping is not None:
                        v = mapping.get(v, v)
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
    """Per bank: the rebuilt stream must hold the same structural ops in the same order, with the
    same arguments and with every jump pointing at the remapped place; block tables must be the
    remapped originals; no unknown tokens; every 32-bit operand aligned."""
    s = info['s']
    m = {k: v for k, v in info['mapping'].items() if isinstance(k, int)}
    problems = []
    bi = 0
    for k, (slot, tab, st, en) in enumerate(s.sections):
        a, ia, bad_a = linear_ops(s.d, [(st, en)], m)
        b, ib, bad_b = linear_ops(out, info['segs'][k])
        b = [x for x in b if not (x[0] == 0x8016 and x[1] in info['extra_jumps'])]
        if bad_b:
            problems.append(('bank %d' % slot, bad_b[:3]))
        if a != b:
            n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            problems.append(('bank %d ops differ at #%d of %d/%d' % (slot, n, len(a), len(b)), a[n:n + 2], b[n:n + 2]))
        for op in (0x8009, 0x800A, 0x8019, 0x802D, 0x8031, 0x8057):
            if ia[op] != ib[op]:
                problems.append(('bank %d inline op %04x count %d -> %d' % (slot, op, ia[op], ib[op]),))
        for e in range((st - tab) // 4):
            v = s.blocks[bi]
            bi += 1
            nv = struct.unpack_from('<I', out, info['new_tab'][k] + 4 * e)[0]
            if e == 0:
                if nv != info['dict_off']:
                    problems.append(('bank %d dictionary pointer' % slot, nv))
                continue
            if nv != (m[v] if v else 0):
                problems.append(('bank %d table entry %d' % (slot, e), v, nv))
                break
    return problems


if __name__ == '__main__':
    for name in sys.argv[1:]:
        rows = json.load(open('work/translation/en/scenes/%s.json' % name, encoding='utf-8'))
        path = 'work/source/winbin/%s.bin' % name[1:]
        out, rep, info = fit(path, rows)
        problems = verify(path, out, info)
        show = {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}
        print(name, os.path.getsize(path), '->', show, 'verify:', problems if problems else 'ok')
