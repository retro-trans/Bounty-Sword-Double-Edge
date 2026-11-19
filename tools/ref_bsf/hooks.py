"""MIPS hooks for the English build (assembled with tools/masm.py).

Two blocks of code/data, both placed in areas that are zero in the original files and
stayed zero in every RAM dump taken so far (boot, name entry, first scene):

  EXE   0x8005DEE0 (0x404 bytes free)   cursor-path VWF + width table
  OVL1  0x80128838 (0x458 bytes free)   dialogue VWF + packed-token fetch + pair table

Patch sites (original instruction -> new):
  0x80018F7C  jal 0x80018F94        -> jal vwf_cursor        (glyph draw wrapper, EXE)
  0x8011F934  jal 0x800192C0        -> jal vwf_dialogue      (dialogue glyph add, overlay 1)
  0x80121840, 0x801227D0, 0x80123B48    same call, same hook (name insert, inline number,
                                        telop text read linearly from the block)
  overlay 20 file offset 0xA48C (0x80154E30)  jal 0x800192C0 -> jal vwf_telop
                                        (opening narration printer: x += 13 per glyph, wrap at 20)
  0x8011F5E0  7 instructions (token fetch)      -> jal fetch + nops
  0x8011F9BC  13 instructions (peek next glyph) -> j peek + nops

Width table: one nibble per glyph code (0 = keep the game's fixed advance).
Pair table: 128 u16 glyph codes; a script token 0x1000 + a*128 + b prints pair[a] then pair[b];
a token 0x5000 + i prints word i of the scene's own dictionary (tools/relink.py).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masm import assemble
import enfont

EXE_BASE = 0x8005DEE0
EXE_ROOM = 0x404
OVL_BASE = 0x80128838
OVL_ROOM = 0x80128837 + 0x45D - OVL_BASE
OVL1_LOAD = 0x80108EEC
NGLYPH = 0x52B
SPACE = enfont.ENC[' ']

# index -> glyph code for packed pairs (index 127 unused)
PAIR_CHARS = sorted(enfont.ENC, key=lambda c: enfont.ENC[c])
assert len(PAIR_CHARS) <= 127
PAIR_INDEX = {enfont.ENC[c]: i for i, c in enumerate(PAIR_CHARS)}


WIDTH_RANGES = ((0x000, 0x0A1, 0x00), (0x360, 0x380, 0xA2), (0x460, 0x52C, 0xC2))   # lo, hi, table index of lo
WIDTH_ENTRIES = 0xC2 + 0xCC


def width_index(g):
    for lo, hi, base in WIDTH_RANGES:
        if lo <= g < hi:
            return base + g - lo
    return None


def width_table():
    w = enfont.widths()
    t = bytearray((WIDTH_ENTRIES + 1) // 2)
    for g, adv in w.items():
        assert 1 <= adv <= 15
        i = width_index(g)
        assert i is not None, hex(g)
        t[i >> 1] |= adv << (4 if i & 1 else 0)
    return bytes(t)


EXE_SRC = """
; Tokens understood on the cursor path and in the speaker name box:
;   glyph code                       one glyph
;   0x1000 + a*128 + b               pair: pair[a] then pair[b]
;   0x5000 + n                       the pool sequence at word offset n (glyphs / pairs, ended by 0)
; emit_all walks one token and calls the path's glyph routine (in s3) for every glyph.

; ---- cursor path (menus, system messages, every FFFF-ended string): the caller adds the
;      font's fixed advance to the cursor (0x80066A54) after each glyph. Every glyph drawn
;      here moves the cursor by its own width; the fixed advance is taken off once at the end.
;      a0 = draw request (0x800BD608): +4 x, +6 y, +8 glyph code
vwf_cursor:
    addiu sp, sp, -0x20
    sw    ra, 0x10(sp)
    sw    s0, 0x14(sp)
    sw    s3, 0x18(sp)
    lhu   t0, 8(a0)
    move  s0, a0
    addiu v1, t0, -0x6D          ; a lone digit keeps the game's fixed advance: its number
    sltiu v1, v1, 10             ; routines place each digit themselves, and a label that
    beqz  v1, vc_text            ; follows a number would be drawn over its last digit
    nop
    jal   0x80018F94
    nop
    b     vc_done
    nop
vc_text:
    la    s3, cur_glyph
    jal   emit_all
    move  a0, t0
    lui   v1, 0x8006
    lw    a1, 0x639C(v1)         ; font descriptor
    lhu   a2, 0x6A54(v1)         ; cursor x
    lbu   a1, 2(a1)              ; fixed advance
    nop
    subu  a2, a2, a1
    sh    a2, 0x6A54(v1)
vc_done:
    lw    ra, 0x10(sp)
    lw    s0, 0x14(sp)
    lw    s3, 0x18(sp)
    jr    ra
    addiu sp, sp, 0x20

; a0 = glyph, s0 = draw request: draw it and move request x and the cursor by its width
cur_glyph:
    addiu sp, sp, -0x18
    sw    ra, 0x10(sp)
    sh    a0, 8(s0)
    jal   0x80018F94
    move  a0, s0
    lhu   a0, 8(s0)
    jal   glyph_width
    nop
    lui   v1, 0x8006
    lw    a1, 0x639C(v1)
    bnez  v0, cg_w
    nop
    lbu   v0, 2(a1)              ; no table width: the font's own advance
    nop
cg_w:
    lhu   a1, 4(s0)
    lhu   a2, 0x6A54(v1)
    addu  a1, a1, v0
    addu  a2, a2, v0
    sh    a1, 4(s0)
    sh    a2, 0x6A54(v1)
    lw    ra, 0x10(sp)
    nop
    jr    ra
    addiu sp, sp, 0x18

; a0 = token, s3 = glyph routine (may use a*, t*, v*; keeps s*)
emit_all:
    addiu sp, sp, -0x20
    sw    ra, 0x10(sp)
    sw    s2, 0x14(sp)
    sw    s4, 0x18(sp)
    move  s2, zero               ; pool read pointer (0: single token)
    addiu t0, a0, -0x5000
    sltiu t1, t0, 0x3000
    beqz  t1, ea_tok
    sll   t0, t0, 1
    lui   s2, %(pool_hi)d
    ori   s2, s2, %(pool_lo)d
    addu  s2, s2, t0
ea_next:
    lhu   a0, 0(s2)
    addiu s2, s2, 2
    beqz  a0, ea_done
    nop
ea_tok:
    addiu t0, a0, -0x1000
    sltiu t1, t0, 0x4000
    beqz  t1, ea_one
    move  s4, zero               ; second glyph of a pair
    la    t2, pairtab
    srl   t1, t0, 7
    sll   t1, t1, 1
    addu  t1, t1, t2
    lhu   a0, 0(t1)
    andi  t0, t0, 0x7F
    sll   t0, t0, 1
    addu  t0, t0, t2
    lhu   s4, 0(t0)
ea_one:
    jalr  s3
    nop
    move  a0, s4
    bnez  a0, ea_one
    move  s4, zero
    bnez  s2, ea_next
    nop
ea_done:
    lw    ra, 0x10(sp)
    lw    s2, 0x14(sp)
    lw    s4, 0x18(sp)
    jr    ra
    addiu sp, sp, 0x20

; ---- speaker name box (overlay 1, three loops: up to 6 tokens, x += 12 each, glyph added
;      with 0x80019350). The caller's x counter (s1 at the first site, s0 at the other two)
;      is corrected by (real width - 12) so the next token follows the text drawn here.
;      in: a0 token, a1 x, a2 y, 0x10(sp) flag of the caller
vwf_name_s1:
    b     vn_go
    li    t9, 1
vwf_name_s0:
    move  t9, zero
vn_go:
    addiu sp, sp, -0x30
    sw    ra, 0x10(sp)
    sw    s3, 0x14(sp)
    sw    s5, 0x18(sp)
    sw    s6, 0x1C(sp)
    sw    s7, 0x20(sp)
    sw    t9, 0x24(sp)
    sw    a1, 0x28(sp)
    lw    s7, 0x40(sp)           ; the caller's stack argument
    move  s5, a1
    move  s6, a2
    la    s3, name_glyph
    jal   emit_all
    nop
    lw    a1, 0x28(sp)
    lw    t9, 0x24(sp)
    subu  v0, s5, a1
    addiu v0, v0, -12
    lw    ra, 0x10(sp)
    lw    s3, 0x14(sp)
    lw    s5, 0x18(sp)
    lw    s6, 0x1C(sp)
    lw    s7, 0x20(sp)
    beqz  t9, vn_s0
    addiu sp, sp, 0x30
    jr    ra
    addu  s1, s1, v0
vn_s0:
    jr    ra
    addu  s0, s0, v0

; a0 = glyph; s5 x (advanced), s6 y, s7 flag
name_glyph:
    addiu sp, sp, -0x20
    sw    ra, 0x18(sp)
    sw    a0, 0x1C(sp)
    li    t0, %(space)d
    beq   a0, t0, ng_w           ; a blank takes no glyph slot
    sw    s7, 0x10(sp)
    move  a1, s5
    move  a2, s6
    jal   0x80019350
    move  a3, zero
ng_w:
    lw    a0, 0x1C(sp)
    jal   glyph_width
    nop
    bnez  v0, ng_a
    nop
    li    v0, 12
ng_a:
    addu  s5, s5, v0
    lw    ra, 0x18(sp)
    nop
    jr    ra
    addiu sp, sp, 0x20

; a0 = glyph code (any value) -> v0 = width, 0 = keep the game's advance. Uses only v0, at.
; The table covers three code ranges: 0-0xA0, 0x360-0x37F, 0x460-0x52B.
glyph_width:
    sltiu at, a0, 0xA1
    bnez  at, gw_tab
    move  v0, a0
    addiu v0, a0, -0x360
    sltiu at, v0, 0x20
    bnez  at, gw_tab
    addiu v0, v0, 0xA2
    addiu v0, a0, -0x460
    sltiu at, v0, 0xCC
    beqz  at, gw_zero
    addiu v0, v0, 0xC2
gw_tab:
    srl   v0, v0, 1
    lui   at, %(wtab_hi)d
    addu  v0, v0, at
    lbu   v0, %(wtab_lo)d(v0)
    andi  at, a0, 1
    sll   at, at, 2
    srlv  v0, v0, at
    jr    ra
    andi  v0, v0, 15
gw_zero:
    jr    ra
    move  v0, zero
    .align 4
pairtab:
"""

OVL_SRC = """
; ---- dialogue: the game puts glyph number idx at grid column idx %% 21 (12 px each).
;      Keep a pen position per line instead, and keep the column counter below 20 so
;      the 20-column auto-wrap never fires on English text.
;      in: a0 glyph, a1 x (window x + grid x), a2 y, a3 colour, 0x10(sp) flag (callee reads it)
vwf_dialogue:
    lui   t0, 0x8006
    lhu   t1, 0x63F4(t0)         ; idx
    la    t4, pen
    move  t2, t1
vd_mod:
    sltiu t3, t2, 21
    bnez  t3, vd_col
    nop
    b     vd_mod
    addiu t2, t2, -21
vd_col:                          ; t2 = column
    lw    t5, 0(t4)              ; pen (loaded before the branch: no write in a load-delay slot)
    nop
    bnez  t2, vd_pen
    nop
    move  t5, zero
vd_pen:
    sll   t3, t2, 1
    addu  t3, t3, t2
    sll   t3, t3, 2              ; column * 12
    subu  a1, a1, t3
    addu  a1, a1, t5
    ; width: nibble from the table, 12 when the glyph keeps the game's advance
    li    t6, 12
    move  t8, ra
    jal   0x%(glyph_width)08X    ; uses only v0, at
    nop
    move  ra, t8
    beqz  v0, vd_adv
    nop
    move  t6, v0
vd_adv:
    addu  t5, t5, t6
    sw    t5, 0(t4)
    ; the game wraps when its column counter reaches 20. Hold the counter at 19 while the
    ; line still has pixel room (any glyph: English, or a Japanese name inside English text);
    ; once the pen passes 240 px the counter runs on and the game's own wrap takes over.
    sltiu t3, t2, 19
    bnez  t3, vd_space
    nop
    sltiu t3, t5, 240
    beqz  t3, vd_space
    nop
    addiu t1, t1, -1             ; the counters are incremented after this call
    sh    t1, 0x63F4(t0)
    lhu   t3, 0x68B4(t0)
    nop
    addiu t3, t3, -1
    sh    t3, 0x68B4(t0)
vd_space:
    li    t3, %(space)d
    beq   a0, t3, vd_skip
    nop
    j     0x800192C0
    nop
vd_skip:                         ; a space takes no glyph slot: return the first free slot index
    lui   t0, 0x800F
    move  v0, zero
vd_find:
    lbu   t3, -0x278(t0)
    nop
    beqz  t3, vd_ret
    addiu t0, t0, 12
    addiu v0, v0, 1
    sltiu t3, v0, 0x7F
    bnez  t3, vd_find
    nop
vd_ret:
    jr    ra
    nop

; ---- opening narration (overlay 20, printer at 0x80154D90). The caller keeps x in s1 and
;      adds 13 after this call, and wraps when its column counter s3 reaches 20.
;      English glyph: move s1 so the net advance is the glyph width, hold s3 below 20,
;      and take no glyph slot for blanks.
vwf_telop:
    move  t8, ra
    jal   0x%(glyph_width)08X
    nop
    move  ra, t8
    move  t6, v0
    beqz  t6, vt_jp
    nop
    addiu t6, t6, -13
    addu  s1, s1, t6
    sltiu t3, s3, 18
    bnez  t3, vt_sp
    nop
    addiu s3, s3, -1
vt_sp:
    li    t3, %(space)d
    bne   a0, t3, vt_draw
    nop
    jr    ra
    nop
vt_jp:
    bnez  a0, vt_draw
    nop
    jr    ra
    nop
vt_draw:
    j     0x800192C0
    nop

; ---- packed tokens. fetch: returns the next script token in v1 and advances the read
;      pointer (0x80066560).
;        0x1000..0x4FFF  pair: 0x1000 + a*128 + b  -> glyphs pair[a], pair[b]
;        0x5000..0x7FFF  word i = token - 0x5000 of the scene's dictionary
;      The dictionary lives in the scene file; its file offset is stored in entry 0 of the
;      current block table (0x8006668C), which the game never uses as a block. Format:
;      u16 offsets (from the dictionary start), then entries [n][n pair-table indices][FF].
;      Pending glyphs are read from 'pend' (a pointer to index bytes ended by FF) and are only
;      used while the read pointer is still where it was when they were queued.
;      Typewriter budget: n glyphs cost about n/2 ticks, so English keeps the Japanese pace.
fetch:
    lui   t0, 0x8006
    lw    v0, 0x6560(t0)
    la    t1, pend
    lw    t3, 0(t1)              ; pending index pointer
    lw    t2, 4(t1)              ; read pointer when queued
    beqz  t3, f_read
    nop
    bne   t2, v0, f_drop
    nop
    lbu   v1, 0(t3)
    nop
    xori  t2, v1, 0xFF
    beqz  t2, f_drop
    addiu t3, t3, 1
    sw    t3, 0(t1)
    b     f_glyph
    nop
f_drop:
    sw    zero, 0(t1)
f_read:
    lhu   v1, 0(v0)
    addiu v0, v0, 2
    sw    v0, 0x6560(t0)
    sltiu t2, v1, 0x1000
    bnez  t2, f_ret
    srl   t2, v1, 15
    bnez  t2, f_ret
    nop
    sw    v0, 4(t1)              ; queue is valid for this read pointer
    sltiu t2, v1, 0x5000
    beqz  t2, f_word
    nop
    ; pair
    addiu v1, v1, -0x1000
    andi  t2, v1, 0x7F
    sb    t2, 8(t1)              ; scratch: [b][FF]
    li    t2, 0xFF
    sb    t2, 9(t1)
    addiu t2, t1, 8
    sw    t2, 0(t1)
    lhu   t2, 0x6A74(t0)
    srl   v1, v1, 7
    addiu t2, t2, 1
    b     f_glyph
    sh    t2, 0x6A74(t0)
f_word:
    addiu v1, v1, -0x5000
    lw    t2, 0x668C(t0)         ; current block table
    sll   v1, v1, 1
    lw    t2, 0(t2)              ; entry 0 = dictionary file offset
    lui   t3, 0x8014
    addiu t3, t3, -0x4D48        ; scene file base 0x8013B2B8
    addu  t2, t2, t3
    addu  v1, v1, t2
    lhu   v1, 0(v1)              ; entry offset
    nop
    addu  t2, t2, v1             ; entry: [n][indices][FF]
    lbu   t3, 0(t2)              ; n
    lbu   v1, 1(t2)              ; first index
    addiu t2, t2, 2
    sw    t2, 0(t1)
    lhu   t2, 0x6A74(t0)
    srl   t3, t3, 1
    addu  t2, t2, t3
    sh    t2, 0x6A74(t0)
f_glyph:                         ; v1 = pair-table index -> glyph code
    la    t3, 0x%(pairtab)08X
    sll   v1, v1, 1
    addu  v1, v1, t3
    lhu   v1, 0(v1)
    nop
f_ret:
    jr    ra
    nop

; replaces the game's 'peek the next token: glyph -> take it, op -> main loop'
peek:
    lui   t0, 0x8006
    lw    a0, 0x6560(t0)
    la    t1, pend
    lw    t3, 0(t1)
    lw    t2, 4(t1)
    beqz  t3, p_look
    nop
    bne   t2, a0, p_look
    nop
    lbu   t3, 0(t3)
    nop
    xori  t3, t3, 0xFF
    bnez  t3, p_take             ; a glyph is still queued
    nop
p_look:
    lh    v0, 0(a0)
    nop
    bltz  v0, p_op
    nop
p_take:
    jal   fetch
    nop
    lui   t0, 0x8006
    sh    v1, 0x6AC8(t0)
    j     0x8011F744
    nop
p_op:
    j     0x8011F5E0
    nop

    .align 4
pen:
    .word 0
pend:
    .word 0                      ; pointer to queued pair-table indices (0 = none)
    .word 0                      ; read pointer the queue belongs to
    .word 0                      ; scratch for a pair's second index: [b][FF]
"""


POOL_TOKEN = 0x5000


def pool_base():
    """Address of the token pool: right after the overlay-1 hook code."""
    src = OVL_SRC % dict(nglyph=NGLYPH, space=SPACE, glyph_width=EXE_BASE, pairtab=EXE_BASE)
    code, _ = assemble(src, OVL_BASE)
    return OVL_BASE + (len(code) + 1 & ~1)


def pool_room():
    """Bytes available for the pool."""
    return OVL_BASE + OVL_ROOM - pool_base()


def build(pool=b''):
    """pool: bytes of the token pool (u16 tokens, sequences ended by 0), see tools/uitext.py
    -> dict: exe_blob, ovl_blob, patches_exe {addr: bytes}, patches_ovl {addr: bytes}"""
    pair = b''.join(struct.pack('<H', enfont.ENC[c]) for c in PAIR_CHARS)
    wt = width_table()
    pb = pool_base()
    # two passes: the width table follows the pair table, whose address depends on the code size
    wtab = 0
    for _ in range(2):
        src = EXE_SRC % dict(space=SPACE, wtab_hi=(wtab + 0x8000) >> 16, wtab_lo=((wtab & 0xFFFF) ^ 0x8000) - 0x8000,
                             pool_hi=pb >> 16, pool_lo=pb & 0xFFFF)
        exe_code, exe_sym = assemble(src, EXE_BASE)
        wtab = exe_sym['pairtab'] + len(pair)
    assert len(exe_code) == exe_sym['pairtab'] - EXE_BASE, (len(exe_code), exe_sym['pairtab'] - EXE_BASE)
    exe_sym['wtab'] = wtab
    exe_blob = bytes(exe_code) + pair + wt
    assert len(exe_blob) <= EXE_ROOM, (len(exe_blob), EXE_ROOM)
    src = OVL_SRC % dict(nglyph=NGLYPH, space=SPACE, glyph_width=exe_sym['glyph_width'], pairtab=exe_sym['pairtab'])
    ovl_code, ovl_sym = assemble(src, OVL_BASE)
    ovl_blob = bytes(ovl_code).ljust(pb - OVL_BASE, b'\0') + bytes(pool)
    ovl_sym['pool'] = pb
    assert len(ovl_blob) <= OVL_ROOM, ('pool too large', len(pool), pool_room())
    ovl_blob = ovl_blob.ljust(OVL_ROOM, b'\0')

    def jal(t):
        return struct.pack('<I', 0x0C000000 | ((t >> 2) & 0x3FFFFFF))

    def j(t):
        return struct.pack('<I', 0x08000000 | ((t >> 2) & 0x3FFFFFF))

    nop = b'\x00' * 4
    return dict(
        exe_blob=exe_blob, ovl_blob=ovl_blob, exe_sym=exe_sym, ovl_sym=ovl_sym,
        patches_exe={0x80018F7C: jal(exe_sym['vwf_cursor'])},
        patches_ovl={0x8011F934: jal(ovl_sym['vwf_dialogue']),
                     0x80121840: jal(ovl_sym['vwf_dialogue']),
                     0x801227D0: jal(ovl_sym['vwf_dialogue']),
                     0x80123B48: jal(ovl_sym['vwf_dialogue']),
                     0x8012127C: jal(exe_sym['vwf_name_s1']),
                     0x8012136C: jal(exe_sym['vwf_name_s0']),
                     0x80121464: jal(exe_sym['vwf_name_s0']),
                     0x8011F5E0: jal(ovl_sym['fetch']) + nop * 6,
                     0x8011F9BC: j(ovl_sym['peek']) + nop * 12},
        expect_exe={0x80018F7C: jal(0x80018F94)},
        expect_ovl=dict([(a, jal(0x800192C0)) for a in (0x8011F934, 0x80121840, 0x801227D0, 0x80123B48)]
                        + [(a, jal(0x80019350)) for a in (0x8012127C, 0x8012136C, 0x80121464)]),
        patches_ovl20={0xA48C: jal(ovl_sym['vwf_telop'])},       # file offsets in OVLFILE entry 20
        expect_ovl20={0xA48C: jal(0x800192C0)},
    )


def pack_pairs(codes):
    """Glyph codes of one text run -> script tokens (pairs where both glyphs are in the pair table)."""
    out = []
    i = 0
    while i < len(codes):
        a = codes[i]
        b = codes[i + 1] if i + 1 < len(codes) else None
        if a in PAIR_INDEX and b in PAIR_INDEX:
            out.append(0x1000 + PAIR_INDEX[a] * 128 + PAIR_INDEX[b])
            i += 2
        else:
            out.append(a)
            i += 1
    return out


if __name__ == '__main__':
    b = build()
    print('exe blob %d / %d bytes, ovl code up to pool %d / %d bytes, pool room %d bytes' % (
        len(b['exe_blob']), EXE_ROOM, b['ovl_sym']['pool'] - OVL_BASE, OVL_ROOM, pool_room()))
    for k in ('vwf_cursor', 'vwf_name_s1', 'vwf_name_s0', 'glyph_width', 'pairtab', 'wtab'):
        print(' %-12s %08X' % (k, b['exe_sym'][k]))
    for k in ('vwf_dialogue', 'fetch', 'peek', 'pen', 'pend', 'pool'):
        print(' %-12s %08X' % (k, b['ovl_sym'][k]))
    print('auto nops', b['exe_sym'].get('__nops_added'), b['ovl_sym'].get('__nops_added'))
