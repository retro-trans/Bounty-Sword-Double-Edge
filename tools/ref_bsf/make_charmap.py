"""Build tools/charmap.json (glyph index -> character) from the MS Gothic match + manual review."""
import json
m = json.load(open('work/source/font_match.json', encoding='utf-8'))
cm = {o['g']: o['ch'] for o in m}
cm[0] = '　'
seq = '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐ'
for i, c in enumerate(seq): cm[0x6d+i] = c
hira = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろわをん'
for i, c in enumerate(hira): cm[0xa1+i] = c
kata = 'ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワン'
for i, c in enumerate(kata): cm[0xf1+i] = c
assert 0xf1+len(kata)-1 == 0x140 and 0xa1+len(hira)-1 == 0xf0
for i, c in enumerate('ｑｒｓｔｕｖｗｘｙｚ'): cm[0x4bc+i] = c
fix = {0x02: '舟', 0x03: 'ー', 0x05: '「', 0x06: '」', 0x08: '－', 0x09: '＝', 0x0b: '％', 0x0c: '＆',
       0x35: '想', 0x4d: '閉', 0x62: '陸', 0x143: '違', 0x14c: '巻', 0x175: '一', 0x19a: '割', 0x19e: '間',
       0x20b: '重', 0x227: '臣', 0x269: '池', 0x27d: '電', 0x2f9: '六', 0x327: 'ヴ', 0x329: '書', 0x32b: '々',
       0x337: '事', 0x33a: '開', 0x349: '歴', 0x368: '…', 0x369: '（', 0x36a: '）', 0x36d: '『', 0x36e: '』',
       0x371: '～', 0x381: '○', 0x388: '関', 0x394: '竪', 0x3cf: '暦', 0x3dc: '冥', 0x3f3: '議', 0x3f8: '、',
       0x3f9: '優', 0x418: '誇', 0x42b: '※', 0x434: '読', 0x446: '圧', 0x466: '！', 0x467: '？', 0x472: 'ヶ',
       0x49e: '枢', 0x4a7: '：', 0x4bb: '△', 0x513: '算', 0x51c: '種', 0x524: '，', 0x525: 'ヲ',
       0x526: '◎', 0x527: '◎', 0x528: '◎', 0x529: '◎', 0x52a: '◎'}
cm.update(fix)
json.dump({'%04x' % k: v for k, v in sorted(cm.items())}, open('tools/charmap.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(cm))
