"""MIPS hooks for the English build (assembled with tools/masm.py).

One block of code/data in overlay 1 (always loaded, load address 0x800F07E0), in an area that is
zero in the file and stayed zero in the RAM dumps taken so far (boot, opening telegram, first dialogue):

  OVL1  0x801014D8 (0x45C bytes free)   dialogue VWF + width tables + packed-token fetch + pair table

Patch sites (overlay 1):
  `jal 0x80019268` (add glyph: a0 glyph, a1 x, a2 y, a3 colour, 0x10(sp) flag) -> `jal vwf_dialogue`
      0x800FAAC8  dialogue text
      0x800FC6B0, 0x800FD42C, 0x800FE06C   same placement code in the name-insert / inline text handlers
  0x800FA724  6 instructions (interpreter loop: read the next token) -> jal fetch + nops
  0x800FAB28  6 instructions (read the next token while the typewriter budget lasts) -> jal fetch,
              sign-extend, branch to the opcode dispatch

VWF: the game puts glyph number idx (0x80062656) at slot idx of a position table: 20 columns of 12 px
per line, 21 slots per line (the 21st is a dummy whose kind byte makes the printer jump to the next
line). The hook keeps its own pen position per line and holds the two slot counters at column 19
while the line still has pixel room, so the game's 20-column wrap does not fire on English text.
Once the pen passes LINE_PX the counters run on and the game's own wrap takes over.

Widths: one nibble per glyph for codes 0..80, plus a short (code, width) list for the other redrawn
cells. Width 0 / not listed = the game's fixed 12 px advance (Japanese glyphs).

Packed tokens (written by tools/relink.py):
  0x1000..0x4FFF  pair: 0x1000 + a*128 + b -> glyphs pairtab[a], pairtab[b]
  0x5000..0x7FFF  word i = token - 0x5000 of the event file's dictionary. The dictionary's file offset
                  is in header slot 17 of the loaded event file (0x8010C84C + 0x44). Format: u16
                  offsets (from the dictionary start), then entries [n][n pair-table indices][FF].
Glyphs still to come are read through 'pend' (a pointer to index bytes ended by FF) and are only used
while the script read pointer (0x80062754) is where it was when they were queued. A pair costs one
typewriter tick and a word about half its length, so English types at about the Japanese pace.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masm import assemble
import enfont

OVL1_LOAD = 0x800F07E0
OVL_BASE = 0x801014D8
OVL_ROOM = 0x801014D7 + 0x45D - OVL_BASE
ADD_GLYPH = 0x80019268
DLG_SHIFT = 4                  # px: dialogue text moved right (the quote glyph's left edge was off the box)
SITES = (0x800FAAC8, 0x800FC6B0, 0x800FD42C, 0x800FE06C)
FETCH_A = 0x800FA724
FETCH_B = 0x800FAB28
OP_DISPATCH = 0x800FA750
LINE_PX = 240
NIB = 81                      # codes 0..80 use the nibble table
DATA_BASE = 0x80104F60        # second free block (0x80104F5C, 0x13C bytes): width tables + pair table
DATA_ROOM = 0x80104F5C + 0x13C - DATA_BASE
TELE_BASE = 0x80101A48        # third free block in overlay 1 (0x106 bytes): narration-printer hook
TELE_ROOM = 0x106
NAMES = 0x8010BA58            # 6-glyph speaker name table (178 x 12 bytes), replaced by the English names
NAMES_ROOM = 178 * 12
NAME_BUF = 0x8010C600         # zero in the file and in every RAM dump: used as an empty glyph string
NAME_BOX = 0x800FC120
NAME_PART2 = 0x800FC208
HERO_BOX = 0x800FC048
# inline speaker name: op 8031 handler and interpreter state 23 (both called 0x800FD190 with the old table)
INLINE_A = 0x800FB0D4         # 9 instructions
INLINE_B = 0x800FE124         # 13 instructions
EXPECT_INLINE_A = (0x3C028006, 0x94432622, 0x24050006, 0x3C048011, 0x2484BA58, 0x00031040, 0x00431021, 0x00021080, 0x0803EC29)
EXPECT_INLINE_B = (0x3C028006, 0x94432622, 0x3C028006, 0x3C048011, 0x2484BA58, 0x24050006, 0xAFBF0010, 0xA44027B4,
                   0x00031040, 0x00431021, 0x00021080, 0x0C03F464, 0x00442021)


# index -> character for packed pairs and dictionary entries
PAIR_CHARS = sorted(enfont.ENC, key=lambda c: enfont.ENC[c])
assert len(PAIR_CHARS) <= 127
PAIR_INDEX = {enfont.ENC[c]: i for i, c in enumerate(PAIR_CHARS)}


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


SRC = """
; in: a0 glyph, a1 x (window x + slot x), a2 y, a3 colour, 0x10(sp) flag (read by the callee)
vwf_dialogue:
    lui   t0, 0x8006
    lhu   t1, 0x2656(t0)         ; slot index
    la    t4, pen
    move  t2, t1
vd_mod:
    sltiu t3, t2, 21
    bnez  t3, vd_col
    nop
    b     vd_mod
    addiu t2, t2, -21
vd_col:                          ; t2 = column
    lw    t5, 0(t4)              ; pen
    nop
    bnez  t2, vd_pen
    nop
    move  t5, zero               ; first glyph of a line
vd_pen:
    sll   t3, t2, 1
    addu  t3, t3, t2
    sll   t3, t3, 2              ; column * 12
    subu  a1, a1, t3
    addu  a1, a1, t5
    addiu a1, a1, %(dlg_shift)d         ; English text starts on the box edge, under the speaker name
    move  t8, ra
    jal   glyph_w                ; t6 = width of a0
    nop
    move  ra, t8
    addu  t5, t5, t6
    sw    t5, 0(t4)
    ; ---- hold the slot counters at column 19 while the line has pixel room
    sltiu t3, t2, 19
    bnez  t3, vd_space
    nop
    sltiu t3, t5, %(line_px)d
    beqz  t3, vd_space
    nop
    addiu t1, t1, -1             ; both counters are incremented after this call
    sh    t1, 0x2656(t0)
    lhu   t3, 0x297E(t0)
    nop
    addiu t3, t3, -1
    sh    t3, 0x297E(t0)
vd_space:
    li    t3, %(space)d
    beq   a0, t3, vd_skip
    nop
    j     0x%(add_glyph)08X
    nop
vd_skip:                         ; a space takes no glyph slot: return the first free slot index
    lui   t0, 0x800D
    addiu t0, t0, 0x5560
    move  v0, zero
vd_find:
    lbu   t3, 0(t0)
    nop
    beqz  t3, vd_ret
    addiu t0, t0, 12
    addiu v0, v0, 1
    sltiu t3, v0, 0xC7
    bnez  t3, vd_find
    nop
vd_ret:
    jr    ra
    nop

; ---- next script token -> a0 (zero-extended), read pointer advanced. Uses only v0, v1, a0-a3:
;      both call sites overwrite those right after, and no other register is known to be free there.
fetch:
    lui   a3, 0x8006
    lw    v0, 0x2754(a3)         ; read pointer
    la    a2, pend
    lw    v1, 0(a2)              ; pointer to queued indices
    lw    a1, 4(a2)              ; read pointer when they were queued
    beqz  v1, f_read
    nop
    bne   a1, v0, f_drop
    nop
    lbu   a0, 0(v1)
    nop
    xori  a1, a0, 0xFF
    beqz  a1, f_drop
    addiu v1, v1, 1
    sw    v1, 0(a2)
    b     f_glyph
    nop
f_drop:
    sw    zero, 0(a2)
f_read:
    lhu   a0, 0(v0)
    addiu v0, v0, 2
    sw    v0, 0x2754(a3)
    sltiu a1, a0, 0x1000
    bnez  a1, f_ret
    srl   a1, a0, 15
    bnez  a1, f_ret
    nop
    sw    v0, 4(a2)              ; the queue belongs to this read pointer
    sltiu a1, a0, 0x5000
    beqz  a1, f_word
    nop
    addiu a0, a0, -0x1000        ; pair
    andi  a1, a0, 0x7F
    sb    a1, 8(a2)              ; scratch: [b][FF]
    li    a1, 0xFF
    sb    a1, 9(a2)
    addiu a1, a2, 8
    sw    a1, 0(a2)
    lhu   a1, 0x2A9C(a3)         ; typewriter budget
    srl   a0, a0, 7
    addiu a1, a1, 1
    b     f_glyph
    sh    a1, 0x2A9C(a3)
f_word:
    addiu a0, a0, -0x5000
    lui   v1, 0x8011
    addiu v1, v1, -0x37B4        ; event file base 0x8010C84C
    lw    a1, 0x44(v1)           ; header slot 17 = dictionary file offset
    sll   a0, a0, 1
    addu  a1, a1, v1             ; dictionary
    addu  a0, a0, a1
    lhu   a0, 0(a0)              ; entry offset
    nop
    addu  a1, a1, a0             ; entry: [n][indices][FF]
    lbu   v1, 0(a1)              ; n
    lbu   a0, 1(a1)              ; first index
    addiu a1, a1, 2
    sw    a1, 0(a2)
    lhu   a1, 0x2A9C(a3)
    srl   v1, v1, 1
    addu  a1, a1, v1
    sh    a1, 0x2A9C(a3)
f_glyph:                         ; a0 = pair-table index -> glyph code
    la    a1, pairtab
    sll   a0, a0, 1
    addu  a0, a0, a1
    lhu   a0, 0(a0)
    nop
f_ret:
    jr    ra
    nop

; ---- a0 = glyph -> t6 = advance in pixels (12 when the glyph keeps the game's fixed advance).
;      Uses only t3, t6, t7.
glyph_w:
    sltiu t3, a0, %(nib)d
    beqz  t3, gw_list
    nop
    srl   t6, a0, 1
    la    t7, wtab
    addu  t6, t6, t7
    lbu   t6, 0(t6)
    andi  t3, a0, 1
    sll   t3, t3, 2
    srlv  t6, t6, t3
    b     gw_w
    andi  t6, t6, 15
gw_list:
    la    t7, xtab
gw_l:
    lhu   t6, 0(t7)
    nop
    beqz  t6, gw_w               ; end of list: t6 = 0
    nop
    beq   t6, a0, gw_hit
    nop
    b     gw_l
    addiu t7, t7, 4
gw_hit:
    lhu   t6, 2(t7)
    nop
gw_w:
    bnez  t6, gw_ret
    nop
    li    t6, 12
gw_ret:
    jr    ra
    nop

; ---- speaker name box (replaces 0x800FC120; 0x800FC208, which drew a second 6-glyph part, now
;      returns at once). a0 = x offset in the box, returns v0 = x after the name.
;      Speaker id = 0x80062630. English names: u16 offsets per id, then [pair-table indices][FF],
;      stored where the 6-glyph name table was (0x%(names)08X).
name_box:
    b     nb_go
    li    t1, 0                  ; mode 0: speaker id, English name bytes
; ---- hero / second name in the box (replaces 0x800FC048): a0 = x offset, a1 = name index;
;      the name is u16 glyphs at 0x800BD316 + index * 16, ended by 0 (mode 1)
hero_box:
    li    t1, 1
nb_go:
    addiu sp, sp, -0x30
    sw    ra, 0x2C(sp)
    sw    s0, 0x18(sp)
    sw    s1, 0x1C(sp)
    sw    s2, 0x20(sp)
    sw    t1, 0x28(sp)
    move  s0, a0
    sll   s1, a1, 4
    lui   v0, 0x800C
    addiu v0, v0, -0x2CEA
    addu  s1, s1, v0             ; hero name (used in mode 1)
    lui   v0, 0x8006
    lw    v1, 0x2800(v0)         ; window number
    lhu   a0, 0x2630(v0)         ; speaker id
    sll   v0, v1, 2              ; window record = 0x800CC748 + window * 0x2A0
    addu  v0, v0, v1
    sll   v0, v0, 2
    addu  v0, v0, v1
    sll   v0, v0, 5
    lui   v1, 0x800D
    addiu v1, v1, -0x38B8
    bnez  t1, nb_loop
    addu  s2, v0, v1
    jal   name_ptr               ; s1 = name bytes
    nop
nb_loop:
    lui   t1, 0x8006
    lbu   t1, 0x2860(t1)         ; glyphs already tracked for the box (the game keeps 16)
    nop
    sltiu t1, t1, 16
    beqz  t1, nb_end
    lw    t1, 0x28(sp)
    nop
    beqz  t1, nb_byte
    nop
    lhu   a0, 0(s1)
    addiu s1, s1, 2
    beqz  a0, nb_end
    nop
    b     nb_have
    nop
nb_byte:
    lbu   t0, 0(s1)
    addiu s1, s1, 1
    xori  t1, t0, 0xFF
    beqz  t1, nb_end
    sll   t0, t0, 1
    la    t1, pairtab
    addu  t0, t0, t1
    lhu   a0, 0(t0)              ; glyph
nb_have:
    lhu   a1, 8(s2)
    lhu   a2, 0xA(s2)
    li    t1, 1
    sw    t1, 0x10(sp)
    addiu a1, a1, 0x40
    addu  a1, a1, s0
    sll   a1, a1, 16
    sra   a1, a1, 16
    addiu a2, a2, 8
    sll   a2, a2, 16
    sra   a2, a2, 16
    sw    a0, 0x24(sp)
    li    t1, %(space)d
    beq   a0, t1, nb_blank       ; a blank takes no tracked slot
    nop
    jal   0x800192CC             ; add a tracked name-box glyph
    move  a3, zero
nb_blank:
    lw    a0, 0x24(sp)
    jal   glyph_w
    nop
    b     nb_loop
    addu  s0, s0, t6
nb_end:
    move  v0, s0
    lw    ra, 0x2C(sp)
    lw    s0, 0x18(sp)
    lw    s1, 0x1C(sp)
    lw    s2, 0x20(sp)
    jr    ra
    addiu sp, sp, 0x30

; a0 = speaker id -> s1 = pointer to its name bytes. Uses t0, t1.
name_ptr:
    lui   t0, %(names_hi)d
    addiu t0, t0, %(names_lo)d
    sll   t1, a0, 1
    addu  t1, t1, t0
    lhu   t1, 0(t1)
    nop
    jr    ra
    addu  s1, t0, t1

    .align 4
pen:
    .word 0
pend:
    .word 0                      ; pointer to queued pair-table indices (0 = none)
    .word 0                      ; read pointer the queue belongs to
    .word 0                      ; scratch for a pair's second index: [b][FF]

; overlay-20 narration: a blank (0) or space glyph draws nothing, so it takes no entry in the
; printer's 200-glyph page buffer (the pen still moves by its width in the caller)
narr_add:
    beqz  a0, na_skip
    addiu t0, zero, %(space)d
    beq   a0, t0, na_skip
    nop
    j     0x%(add_glyph)08X
    nop
na_skip:
    jr    ra
    nop

; ---- old saves: party members keep the name copied from the unit template when they joined, so a
;      save made before the unit names were translated shows Japanese names. Called from the EXE glyph
;      hook (ui_glyph checks that this code is loaded: its first word is the signature) whenever a
;      Japanese glyph (0x81..0xA00) is drawn; part B (pf_b, in the speaker-name table's unused tail)
;      gives each party slot whose name still starts with a glyph below 0x1000 the English name of
;      the unit template it matches (key table pf_tab).
party_fix:
    lui   t9, 0x5046             ; signature
    lui   t0, 0x800C
    lhu   t0, -0x3BC8(t0)        ; the glyph being drawn (draw request 0x800BC430 + 8)
    nop
    addiu t0, t0, -0x81
    sltiu t0, t0, 0x981
    beqz  t0, pf_done
    lui   t4, 0x800D
    addiu t4, t4, -0x6B4C        ; party slot 0 (0x800C94B4)
    j     0x%(pf_b)08X
    addiu t5, t4, 0x1140         ; 24 slots of 0xB8 bytes
pf_done:
    j     0x%(ug_ret)08X
    nop
"""

PF_B = """
pf_slot:
    lhu   t6, 0(t4)
    lhu   t7, 2(t4)
    addiu t0, t6, -1
    sltiu t0, t0, 0xFFF          ; first cell 1..0xFFF: a Japanese name
    beqz  t0, pf_next
    lhu   t1, 8(t4)
    sll   t7, t7, 8
    or    t7, t7, t6
    addu  t7, t7, t1
    andi  t7, t7, 0xFFFF         ; key = (cell0 | cell1 << 8) + cell4
    lui   t8, %(tab_hi)d
    addiu t8, t8, %(tab_lo)d
pf_find:
    lhu   t0, 0(t8)
    lbu   t1, 2(t8)              ; unit template index
    beqz  t0, pf_next
    addiu t8, t8, 4
    bne   t0, t7, pf_find
    li    t0, 0xB8
    multu t1, t0
    lui   t2, 0x8010
    addiu t2, t2, -0x2A0         ; unit templates (overlay 1, 0x800FFD60)
    mflo  t0
    addu  t2, t2, t0
    lw    t0, 0(t2)
    lw    t1, 4(t2)
    lw    t3, 8(t2)
    lw    t6, 12(t2)
    sw    t0, 0(t4)
    sw    t1, 4(t4)
    sw    t3, 8(t4)
    sw    t6, 12(t4)
pf_next:
    addiu t4, t4, 0xB8
    bne   t4, t5, pf_slot
    nop
    j     0x%(pf_done)08X
    nop
"""
PF_SIG = 0x3C195046              # lui t9, 0x5046
UNIT_TPL = 0xF580                # unit templates in overlay 1 (file offset), 0xB8 bytes each


def pf_table():
    """(key, template index) for every translated unit whose Japanese name an old save may hold."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = open(os.path.join(root, 'work', 'source', 'ovl', '001.bin'), 'rb').read()
    out = {}
    for k in list(range(2, 12)) + list(range(14, 23)):     # not the hero / rival (typed names)
        c = struct.unpack_from('<8H', d, UNIT_TPL + k * 0xB8)
        key = ((c[0] | c[1] << 8) + c[4]) & 0xFFFF
        assert 0 < c[0] < 0x1000 and key
        out.setdefault(key, k)
    for k in (0, 12):
        c = struct.unpack_from('<8H', d, UNIT_TPL + k * 0xB8)
        assert ((c[0] | c[1] << 8) + c[4]) & 0xFFFF not in out
    return b''.join(struct.pack('<HBB', key, k, 0) for key, k in out.items()) + bytes(4)


TELE_SRC = """
; ---- overlay 20 narration printers (telegram, epilogues): they add 12 to the pen after each glyph.
;      Replaces their 'jal 0x80019268' (a0 glyph, a1 pen x, a2 y, a3, 0x10(sp) flag).
;      One glyph: move the stored pen by (width - 12) so the game's +12 gives the real width.
;      A pair token: draw both glyphs and move the pen by (w1 + w2 - 12).
tele_bc:
    b     tele_go
    li    t9, 0x67BC             ; pen at 0x801667BC (0x80121290)
tele_b4:
    li    t9, 0x67B4             ; pen at 0x801667B4 (0x801210A4)
tele_go:
    addiu t0, a0, -0x1000
    sltiu t1, t0, 0x4000
    bnez  t1, tele_pair
    nop
    move  t8, ra
    jal   0x%(glyph_w)08X
    nop
    move  ra, t8
    lui   t3, 0x8016
    addu  t3, t3, t9
    lhu   t7, 0(t3)
    addiu t6, t6, -12
    addu  t7, t7, t6
    j     0x%(add_glyph)08X
    sh    t7, 0(t3)
tele_pair:
    addiu sp, sp, -0x38
    sw    ra, 0x30(sp)
    sw    s0, 0x28(sp)
    sw    s1, 0x2C(sp)
    sw    t9, 0x20(sp)
    lw    t1, 0x48(sp)           ; the caller's flag argument
    sw    a1, 0x14(sp)
    sw    a2, 0x18(sp)
    sw    a3, 0x1C(sp)
    sw    t1, 0x10(sp)
    srl   s0, t0, 7
    andi  s1, t0, 0x7F
    sll   s0, s0, 1
    sll   s1, s1, 1
    lui   t1, %(pt_hi)d
    addiu t1, t1, %(pt_lo)d
    addu  s0, s0, t1
    addu  s1, s1, t1
    jal   0x%(add_glyph)08X       ; first glyph at the pen (0x80019268 leaves a0 alone)
    lhu   a0, 0(s0)
    jal   0x%(glyph_w)08X
    nop
    lw    a1, 0x14(sp)
    move  s0, t6                 ; w1
    addu  a1, a1, t6
    lw    a2, 0x18(sp)
    lw    a3, 0x1C(sp)
    jal   0x%(add_glyph)08X       ; second glyph
    lhu   a0, 0(s1)
    jal   0x%(glyph_w)08X
    nop
    lw    t9, 0x20(sp)
    addu  t6, t6, s0
    addiu t6, t6, -12
    lui   t3, 0x8016
    addu  t3, t3, t9
    lhu   t7, 0(t3)
    lw    ra, 0x30(sp)
    addu  t7, t7, t6
    sh    t7, 0(t3)
    lw    s0, 0x28(sp)
    lw    s1, 0x2C(sp)
    jr    ra
    addiu sp, sp, 0x38
"""

SITE_A = """
    jal   0x%(fetch)08X
    nop
    nop
    nop
    nop
    nop
"""
SITE_B = """
    jal   0x%(fetch)08X
    nop
    sll   a1, a0, 16
    sra   a1, a1, 16
    bltz  a1, 0x%(dispatch)08X
    nop
"""
# original instruction words at the two fetch sites (checked before patching)
EXPECT_A = (0x3C038006, 0x8C622754, 0x00000000, 0x94440000, 0x24420002, 0xAC622754)
EXPECT_B = (0x8C622754, 0x00000000, 0x84450000, 0x24420002, 0x04A0FF05, 0xAC622754)


def tables():
    w = enfont.widths()
    nib = bytearray((NIB + 1) // 2)
    xt = b''
    for g, adv in sorted(w.items()):
        assert 1 <= adv <= 15
        if g < NIB:
            nib[g >> 1] |= adv << (4 if g & 1 else 0)
        else:
            xt += struct.pack('<HH', g, adv)
    return bytes(nib), xt + struct.pack('<HH', 0, 0)


def build():
    """-> dict: ovl_blob, patches_ovl {addr: bytes}, expect_ovl {addr: bytes}, sym"""
    nib, xt = tables()
    nib += bytes(-len(nib) % 4)
    pair = b''.join(struct.pack('<H', enfont.ENC[c]) for c in PAIR_CHARS)
    pair += bytes(-len(pair) % 4)
    wtab = DATA_BASE
    xtab = wtab + len(nib)
    pairtab = xtab + len(xt)
    data = nib + xt + pair
    assert len(data) <= DATA_ROOM, (len(data), DATA_ROOM)
    names_used = len(names_blob(trim=True))
    pf_b = NAMES + ((names_used + 3) & ~3)
    pf_tab = DATA_BASE + len(nib) + len(xt) + len(pair)
    data = data + pf_table()
    assert len(data) <= DATA_ROOM, (len(data), DATA_ROOM)
    src = SRC % dict(pf_b=pf_b, ug_ret=ug_ret(), nib=NIB, line_px=LINE_PX, dlg_shift=DLG_SHIFT, space=enfont.SPACE, add_glyph=ADD_GLYPH, names=NAMES,
                     names_hi=(NAMES + 0x8000) >> 16, names_lo=((NAMES & 0xFFFF) ^ 0x8000) - 0x8000,
                     buf_hi=(NAME_BUF + 0x8000) >> 16, buf_lo=((NAME_BUF & 0xFFFF) ^ 0x8000) - 0x8000)
    code, sym = assemble(src, OVL_BASE, symbols={'wtab': wtab, 'xtab': xtab, 'pairtab': pairtab})
    blob = bytes(code)
    assert len(blob) <= OVL_ROOM, (len(blob), OVL_ROOM)
    sym['wtab'] = wtab
    sym['xtab'] = xtab
    sym['pairtab'] = pairtab

    def jal(t):
        return struct.pack('<I', 0x0C000000 | ((t >> 2) & 0x3FFFFFF))
    patches = {a: jal(sym['vwf_dialogue']) for a in SITES}
    expect = {a: jal(ADD_GLYPH) for a in SITES}
    a_code, _ = assemble(SITE_A % dict(fetch=sym['fetch']), FETCH_A)
    b_code, _ = assemble(SITE_B % dict(fetch=sym['fetch'], dispatch=OP_DISPATCH), FETCH_B)
    assert len(a_code) == 24 and len(b_code) == 24
    patches[FETCH_A] = bytes(a_code)
    patches[FETCH_B] = bytes(b_code)
    expect[FETCH_A] = struct.pack('<6I', *EXPECT_A)
    expect[FETCH_B] = struct.pack('<6I', *EXPECT_B)
    # name box: 0x800FC120 -> j name_box; 0x800FC208 -> return a0
    patches[NAME_BOX] = bytes(assemble('j 0x%08X\nnop' % sym['name_box'], NAME_BOX)[0])
    patches[HERO_BOX] = bytes(assemble('j 0x%08X'%sym['hero_box']+chr(10)+'nop', HERO_BOX)[0])
    expect[HERO_BOX] = struct.pack('<2I', 0x27BDFFD0, 0xAFB00018)
    patches[NAME_PART2] = bytes(assemble('jr ra\nmove v0, a0', NAME_PART2)[0])
    # op 8031 (inline speaker name) is not used by the script: both sites print an empty name
    a_src = chr(10).join(['lui a0, 0x%04X' % ((NAME_BUF + 0x8000) >> 16), 'addiu a0, a0, %d' % (((NAME_BUF & 0xFFFF) ^ 0x8000) - 0x8000),
                          'addiu a1, zero, 6', 'j 0x800FB0A4', 'nop', 'nop', 'nop', 'nop', 'nop'])
    patches[INLINE_A] = bytes(assemble(a_src, INLINE_A)[0])
    b_src = chr(10).join(['lui v0, 0x8006', 'sw ra, 0x10(sp)', 'sh zero, 0x27B4(v0)',
                          'lui a0, 0x%04X' % ((NAME_BUF + 0x8000) >> 16), 'addiu a0, a0, %d' % (((NAME_BUF & 0xFFFF) ^ 0x8000) - 0x8000),
                          'addiu a1, zero, 6'] + ['nop'] * 5 + ['jal 0x800FD190', 'nop'])
    patches[INLINE_B] = bytes(assemble(b_src, INLINE_B)[0])
    assert len(patches[INLINE_A]) == 36 and len(patches[INLINE_B]) == 52
    expect[INLINE_A] = struct.pack('<9I', *EXPECT_INLINE_A)
    expect[INLINE_B] = struct.pack('<13I', *EXPECT_INLINE_B)
    expect[NAME_BOX] = struct.pack('<2I', 0x27BDFFD0, 0xAFB00018)
    expect[NAME_PART2] = struct.pack('<2I', 0x27BDFFD0, 0xAFB00018)
    tcode, tsym = assemble(TELE_SRC % dict(glyph_w=sym['glyph_w'], add_glyph=sym['narr_add'],
                                           pt_hi=(pairtab + 0x8000) >> 16, pt_lo=((pairtab & 0xFFFF) ^ 0x8000) - 0x8000),
                           TELE_BASE)
    assert len(tcode) <= TELE_ROOM, (len(tcode), TELE_ROOM)
    sym.update(tsym)
    patches[TELE_BASE] = bytes(tcode)
    expect[TELE_BASE] = bytes(TELE_ROOM)
    bcode, _ = assemble(PF_B % dict(pf_done=sym['pf_done'], tab_hi=(pf_tab + 0x8000) >> 16,
                                    tab_lo=((pf_tab & 0xFFFF) ^ 0x8000) - 0x8000), pf_b)
    nb = bytearray(names_blob())
    o = pf_b - NAMES
    assert o + len(bcode) <= NAMES_ROOM and not any(nb[o:o + len(bcode)]), (o, len(bcode))
    nb[o:o + len(bcode)] = bytes(bcode)
    sym['pf_b'] = pf_b
    sym['pf_tab'] = pf_tab
    patches[NAMES] = bytes(nb)
    patches[DATA_BASE] = bytes(data)
    expect[DATA_BASE] = bytes(DATA_ROOM)              # must be free
    return dict(ovl_blob=blob, patches_ovl=patches, expect_ovl=expect, sym=sym)


def names_blob(trim=False):
    """English speaker names from work/glossary/speakers.json: u16 offsets per id (from the blob start),
    then [pair-table indices][FF] per distinct name. Must fit in the old 6-glyph table."""
    import json
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sp = json.load(open(os.path.join(root, 'work', 'glossary', 'speakers.json'), encoding='utf-8'))
    assert len(sp) == 178
    names = [e.get('box') or e['en'] or '' for e in sp]
    for n in names:
        assert sum(1 for c in n if c != ' ') <= 16, n      # the box tracks at most 16 glyphs (0x80062998)
    body = bytearray()
    at = {}
    base = 2 * len(names)
    offs = []
    for n in names:
        if n not in at:
            at[n] = base + len(body)
            body += bytes([PAIR_INDEX[enfont.ENC[c]] for c in n] + [0xFF])
        offs.append(at[n])
    blob = struct.pack('<%dH' % len(names), *offs) + bytes(body)
    assert len(blob) <= NAMES_ROOM, (len(blob), NAMES_ROOM)
    if trim:
        return blob
    return blob + bytes(NAMES_ROOM - len(blob))


FIXED_BASE = 0x0A00            # 0x0A00 + glyph: drawn at the fixed advance (below the pair tokens 0x1000+)
SHADOW_TEST = 0x80019168       # glyph renderer: which glyphs get the built-in 1-px drop shadow
SHADOW_TEST_EXPECT = (0x92230000, 0x24020001, 0x10620030, 0x00000000, 0x92220001, 0x00000000, 0x1440002C, 0x26E20001)
MENU_TINT = 0x80019084
GLYPH_LIMIT = (0x80019290, 0x800192F0)   # 'slti v0, t0, 0xC8' in the two add_glyph copies
EXE_CODE = 0x80060A60          # zero in the file and in every RAM dump (0x202 bytes)
EXE_CODE_ROOM = 0x80060A5C + 0x202 - EXE_CODE
EXE_DATA = 0x800608D0          # same (0x190 bytes from 0x800608CA): width + pair tables (EXE copy)
EXE_DATA_ROOM = 0x800608CA + 0x190 - EXE_DATA
UI_DRAW = 0x80018DF4
UI_DRAW_EXPECT = (0x3C028006, 0x8C4228B4)      # lui v0, 0x8006 ; lw v0, 0x28B4(v0)

EXE_SRC = """
ui_glyph:
    ; the name-entry field (overlay 20 window-printer call returning to 0x80127760; window printer
    ; plain-glyph path returning to 0x80026F0C; helper 0x80026CF0 returning to 0x80026D94) keeps the
    ; original fixed cells, so typed letters sit over their per-cell underlines
    lui   t0, 0x8002
    addiu t0, t0, 0x6D94
    bne   ra, t0, ug_go
    lw    t1, 0x10(sp)
    addiu t0, t0, 0x0178         ; 0x80026F0C
    bne   t1, t0, ug_go
    lw    t1, 0x3C(sp)
    lui   t0, 0x8012
    addiu t0, t0, 0x7760
    beq   t1, t0, ui_orig
    nop
ug_go:
    lui   t0, %(pf_hi)d
    lw    t0, %(pf_lo)d(t0)
    lui   t1, 0x3C19
    ori   t1, t1, 0x5046
    bne   t0, t1, ug_go2           ; overlay 1 (with party_fix) not loaded
    nop
    j     0x%(pf)08X               ; old-save party names; returns to ug_go2
    nop
ug_go2:
    addiu sp, sp, -0x28
    sw    ra, 0x20(sp)
    sw    s0, 0x18(sp)
    sw    s1, 0x1C(sp)
    lui   s0, 0x800C
    addiu s0, s0, -0x3BD0        ; draw request
    lhu   a0, 8(s0)
    nop
    addiu t0, a0, -0x0A00        ; FIXED_BASE + glyph: that glyph at the fixed advance (name-entry grid)
    sltiu t1, t0, 0x600
    bnez  t1, ug_fixed
    addiu t0, a0, -19
    sltiu t0, t0, 10
    bnez  t0, ug_plain           ; a lone digit keeps the fixed advance
    addiu t0, a0, -0x1000
    sltiu t1, t0, 0x4000
    beqz  t1, ug_single
    nop
    srl   t1, t0, 7              ; pair: pairtab[a], pairtab[b]
    andi  s1, t0, 0x7F
    sll   t1, t1, 1
    la    t2, xpairtab
    addu  t1, t1, t2
    jal   ug_one
    lhu   a0, 0(t1)
    sll   s1, s1, 1
    la    t2, xpairtab
    addu  s1, s1, t2
    jal   ug_one
    lhu   a0, 0(s1)
    b     ug_fix
    nop
ug_single:
    jal   ug_one
    nop
ug_fix:
    lui   t0, 0x8006
    lw    t1, 0x2608(t0)         ; font descriptor
    lhu   t2, 0x2A8C(t0)         ; cursor
    lbu   t1, 2(t1)              ; fixed advance
    nop
    subu  t2, t2, t1
    sh    t2, 0x2A8C(t0)
    b     ug_ret
    nop
ug_fixed:
    addiu t0, a0, -0x0A00
    sh    t0, 8(s0)
ug_plain:
    jal   ui_orig
    nop
ug_ret:
    lw    ra, 0x20(sp)
    lw    s0, 0x18(sp)
    lw    s1, 0x1C(sp)
    jr    ra
    addiu sp, sp, 0x28

; a0 = glyph: draw it at the request, then move request x and the cursor by its width
ug_one:
    addiu sp, sp, -0x20
    sw    ra, 0x18(sp)
    sh    a0, 8(s0)
    jal   ui_orig
    sw    a0, 0x10(sp)
    lw    a0, 0x10(sp)
    jal   xglyph_w
    nop
    lhu   t0, 4(s0)
    lui   t1, 0x8006
    lhu   t2, 0x2A8C(t1)
    addu  t0, t0, t6
    addu  t2, t2, t6
    sh    t0, 4(s0)
    sh    t2, 0x2A8C(t1)
    lw    ra, 0x18(sp)
    nop
    jr    ra
    addiu sp, sp, 0x20

; the original 0x80018DF4: its two displaced instructions, then the rest of it
ui_orig:
    lui   v0, 0x8006
    lw    v0, 0x28B4(v0)
    j     0x80018DFC
    nop

; a0 = glyph -> t6 = advance (12 when the glyph keeps the fixed advance). Uses t3, t6, t7.
xglyph_w:
    sltiu t3, a0, %(nib)d
    beqz  t3, xg_list
    nop
    srl   t6, a0, 1
    la    t7, xwtab
    addu  t6, t6, t7
    lbu   t6, 0(t6)
    andi  t3, a0, 1
    sll   t3, t3, 2
    srlv  t6, t6, t3
    b     xg_w
    andi  t6, t6, 15
xg_list:
    la    t7, xxtab
xg_l:
    lhu   t6, 0(t7)
    nop
    beqz  t6, xg_w
    nop
    beq   t6, a0, xg_hit
    nop
    b     xg_l
    addiu t7, t7, 4
xg_hit:
    lhu   t6, 2(t7)
    nop
xg_w:
    bnez  t6, xg_ret
    nop
    li    t6, 12
xg_ret:
    jr    ra
    nop
"""


def ug_ret():
    """Address of ug_go2 in the EXE hook (where party_fix returns); the layout does not depend on pf."""
    pf = 0x80100000
    _, sym = assemble(EXE_SRC % dict(nib=NIB, pf=pf, pf_hi=0x8010, pf_lo=0), EXE_CODE,
                      symbols={'xwtab': EXE_DATA, 'xxtab': EXE_DATA, 'xpairtab': EXE_DATA})
    return sym['ug_go2']


def build_exe():
    """-> dict: patches {addr: bytes}, expect {addr: bytes}, sym"""
    nib, xt = tables()
    nib += bytes(-len(nib) % 4)
    pair = b''.join(struct.pack('<H', enfont.ENC[c]) for c in PAIR_CHARS)
    pair += bytes(-len(pair) % 4)
    xwtab = EXE_DATA
    xxtab = xwtab + len(nib)
    xpairtab = xxtab + len(xt)
    data = nib + xt + pair
    assert len(data) <= EXE_DATA_ROOM, (len(data), EXE_DATA_ROOM)
    pf = build()['sym']['party_fix']
    code, sym = assemble(EXE_SRC % dict(nib=NIB, pf=pf, pf_hi=(pf + 0x8000) >> 16,
                                        pf_lo=((pf & 0xFFFF) ^ 0x8000) - 0x8000), EXE_CODE,
                         symbols={'xwtab': xwtab, 'xxtab': xxtab, 'xpairtab': xpairtab})
    code = bytes(code)
    assert len(code) <= EXE_CODE_ROOM, (len(code), EXE_CODE_ROOM)
    patches = {EXE_CODE: code, EXE_DATA: data,
               UI_DRAW: bytes(assemble('j 0x%08X' % sym['ui_glyph'] + chr(10) + 'nop', UI_DRAW)[0])}
    expect = {EXE_CODE: bytes(EXE_CODE_ROOM), EXE_DATA: bytes(EXE_DATA_ROOM),
              UI_DRAW: struct.pack('<2I', *UI_DRAW_EXPECT)}
    # glyph list (200 entries of 12 bytes at 0x800D5560): when it is full, add_glyph (both copies)
    # wrote entry 200, i.e. 0x800D5EC0, the sound library's tick rate (60) right after the list, and
    # music then plays at the wrong tempo. English needs more glyphs than Japanese, so a full list is
    # reachable: search entries 0..198 only, so a full list reuses entry 199 and never writes past it.
    # drop shadow: the renderer draws a second sprite 1 px down-right with the CLUT group 0x60 above
    # the glyph's (its code already handles colour 0x30), but only for colour 0 with flag != 1
    # (dialogue). Menu windows (beige) draw colour 0x30 with flag 1; their text is now black
    # (fontgrad.py), so let colours 0 and 0x30 both take the shadow, whatever the flag.
    patches[SHADOW_TEST] = bytes(assemble(chr(10).join([
        'lbu   v0, 1(s1)', 'nop', 'sltiu v1, v0, 0x31', 'nop', 'nop', 'nop',
        'beqz  v1, 0x80019234', 'addiu v0, s7, 1']), SHADOW_TEST)[0])
    expect[SHADOW_TEST] = struct.pack('<8I', *SHADOW_TEST_EXPECT)
    # colour 0x30 sprites are tinted 0xC0 + byte 2 (1.5x): 0xFF (2x) lightens the menu shadow
    # (the black text stays black); dialogue (colour 0, tint 0x80) is unaffected
    patches[MENU_TINT] = struct.pack('<I', 0x244200FF)          # addiu v0, v0, 0xFF
    expect[MENU_TINT] = struct.pack('<I', 0x244200C0)           # addiu v0, v0, 0xC0
    for a in GLYPH_LIMIT:
        patches[a] = struct.pack('<I', 0x290200C7)            # slti v0, t0, 199
        expect[a] = struct.pack('<I', 0x290200C8)             # slti v0, t0, 200
    return dict(patches=patches, expect=expect, sym=sym)

if __name__ == '__main__':
    h = build()
    print('overlay 1 hook: %d / %d bytes at %08X' % (len(h['ovl_blob']), OVL_ROOM, OVL_BASE))
    print({k: hex(v) for k, v in h['sym'].items() if k in ('vwf_dialogue', 'fetch', 'glyph_w', 'name_box', 'hero_box', 'pen', 'pend', 'wtab', 'xtab', 'pairtab')})
    print('names blob', len(names_blob().rstrip(b'\0')), 'of', NAMES_ROOM)


# ================================================================ EXE: menus and system text
# Every menu glyph goes through 0x80018DF4 (no arguments: draw request at 0x800BC430, +4 x, +6 y,
# +8 glyph); every caller then adds the font's fixed advance (font descriptor 0x80062608, byte 2) to
# the cursor 0x80062A8C. The entry of 0x80018DF4 jumps to ui_glyph, which:
#   * draws a lone digit as before (number columns stay aligned);
#   * expands a pair token 0x1000 + a*128 + b into pairtab[a], pairtab[b];
#   * moves the request x and the cursor by each glyph's own width, then takes the fixed advance
#     off the cursor once so the caller's addition gives the real width.
