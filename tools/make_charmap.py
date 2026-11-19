"""Finalize charmap: auto-match (tools/build_table.py) + manual fixes for the custom kana/ASCII glyphs.
Output work/glossary/charmap.json : {"<glyph index>": "<char>"} ; script code == glyph index."""
import json
t = json.load(open('work/glossary/charmap_auto.json', encoding='utf-8'))
m = {x['idx']: x['ch'] for x in t}
head = [' ', '、', '。', '：', '？', '！', '々', 'ー', '…', '（', '）', '「', '」', '『', '』', '－', '×', '＝', '％']
for i, c in enumerate(head): m[i] = c
for i in range(10): m[19 + i] = chr(0xff10 + i)
for i in range(26): m[29 + i] = chr(0xff21 + i)
for i in range(26): m[55 + i] = chr(0xff41 + i)
hira = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろわをん'
kata = 'ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヲンヴ'
for i, c in enumerate(hira): m[81 + i] = c
for i, c in enumerate(kata): m[161 + i] = c
assert 161 + len(kata) == 243 and 81 + len(hira) == 161
fix = {255: '議', 264: '違', 344: '開', 374: '間', 375: '関', 489: '警', 530: '誇', 545: '口', 613: '算', 641: '事',
       703: '重', 793: '枢', 848: '想', 975: '電', 1010: '読', 1211: '優', 1246: '陸', 1260: '亮', 1274: '暦',
       1285: '六', 1287: '論', 1314: '＋', 1318: '○', 1320: '斬', 1321: '◎', 1322: '●'}
m.update(fix)
json.dump({str(k): v for k, v in sorted(m.items())}, open('work/glossary/charmap.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(m))
