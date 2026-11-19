"""Build work/glossary/speakers.json (note: the 'box' field, a <=16-letter short form for the name box, is kept by hand in the JSON; re-running this script drops it) from the speaker name table in overlay 1 (file offset 0x1B278,
178 entries of 6 glyphs; a long name uses two consecutive entries) and fill the English names.
Speaker id = argument of script ops 8002 / 804F / 8024 / 8033 / 8061 / 8064.
No English release or wiki exists for this game: every spelling is a romanization. Cast names follow
car makes and chassis codes (TVR Cerbera / Griffith, Jaguar, Mazda FD3S / SA22C, Lotus Elise, Ford
Cortina), as the first game's follow gun makers; those spellings are used. '~' = second half of the
previous entry's name."""
import json, os, struct, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bs2_text as T

EN = """??????|Kane|Sera|Alice|Cerbera|Griffith|Ixion|Faust|Professor|FD-3S|Aerial|Ozunu|Toryu|Ayame|Tethys|Robun|Diana|Jaguar|Parsifal|General|Major|Captain|Sorcery Unit Captain|Combat Captain|Squad Leader|Garrison Captain|Platoon Leader|Barkeep|Trooper|Machine Soldier|Military A|Soldier A|Soldier B|Mech Infantry A|Mech Infantry B|Soldier A|Soldier B|Heavy Infantry A|Heavy Infantry B|Volunteer A|Volunteer B|Soldier|McAuliffe|Undead|Zombie Knight|Ymir|Fluid Automaton|Automaton|Modified Automaton|Plant Automaton|Composite Automaton|Hydroid|Juggernaut|Guide|Namer|Item Seller|Void Seller|Informant|Advisor|Fortune Granny|Girl|Drifter|Zodiac Demigods|SA-22C|Lancelot|Old Man|Little Girl|Company Commander|Tsuchimikado|Ange|Division Commander|Airborne Trooper|Elise|Cortina|Cerberus|Zombie|Dark Land's|Item Seller|Traveling Artisan|Demon Void|Seller|Voice|Raggadol|Diane|General Sigurd|Tethys|1099|9174|3367|0198|Forest Warden|Alice 2nd|Ayame 2nd|Laius|Hector|Citizen A|Citizen B|Citizen C|Man|War God Ares|Beauty God Venus|Messenger God|Hermes|Silence God Selene|Sun God|Apollo|Wisdom God|Mercury|Beauty God Aphrodite|~|Underworld God|Pluto|Time God Cronus|Sky God|Uranus|Sea God|Poseidon|Great God Zeus|Zodiac Twelve Gods|Assyrian Soldier|Thief|Hector's|Subordinate|Dragon Emperor|~|Weaponsmith|McAuliffe|Zodiac Demigods|Carrier|Rheinmetall Major|~|Rheinmetall Platoon Leader|~|Rheinmetall Division Commander|~|Rheinmetall Soldier|~|Rheinmetall Chemical Trooper|~|Rheinmetall Heavy Infantry A|~|Rheinmetall Heavy Infantry B|~|Rhodes Army Captain|~|Rhodes Army Soldier|~|Assyrian Trooper|~|Assyrian Combat Captain|~|Assyrian Company Commander|~|Assyrian Soldier A|~|Assyrian Soldier B|~|Folgore Squad Leader|~|Folgore Volunteer A|~|Folgore Volunteer B|~|Machine|Rhodes Squad Leader|~|Romulus Squad Leader|~|Rheinmetall Soldier A|~|Rheinmetall Soldier B|~|Rheinmetall Airborne Trooper|~|Rheinmetall Soldier A|~|Rheinmetall Soldier B|~""".split('|')
UNSURE = {4: 'TVR Cerbera assumed', 10: 'or Ariel', 11: 'Ozunu (En no Ozunu)', 12: 'Toryu', 17: 'Jaguar, written Jagyua', 29: 'reading of the term',
          42: 'McAuliffe', 45: 'Ymir', 46: 'term', 52: 'Juggernaut', 54: 'renames units', 62: 'term', 68: 'Tsuchimikado', 69: 'Ange or Anju',
          72: 'Lotus Elise assumed', 73: 'Ford Cortina assumed', 82: 'same spelling as the first game', 93: 'Laius or Laios', 110: 'kanji read by eye',
          123: 'two-entry name Dragon Emperor', 143: 'Rhodes', 157: 'Folgore'}
ST, N = 0x1B278, 178

if __name__ == '__main__':
    assert len(EN) == N, len(EN)
    d = open('work/source/ovl/001.bin', 'rb').read()
    used = collections.Counter()
    for p in glob.glob('work/translation/en/scenes/*.json'):
        if p.endswith('.en.json'): continue
        for r in json.load(open(p, encoding='utf-8')):
            if r['spk']: used[int(r['spk'].split(':')[1].split(',')[0], 16)] += 1
    out = []
    for i in range(N):
        jp = T.decode_words(struct.unpack_from('<6H', d, ST + i * 12)).rstrip()
        e = dict(id=i, jp=jp, en='' if EN[i] == '~' else EN[i], rows=used.get(i, 0))
        if EN[i] == '~': e['note'] = 'second half of the previous entry (the name spans two entries)'
        elif i in UNSURE: e['note'] = 'unconfirmed: ' + UNSURE[i]
        out.append(e)
    json.dump(out, open('work/glossary/speakers.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(len(out), 'speakers;', sum(1 for e in out if e.get('note', '').startswith('unconfirmed')), 'unconfirmed')
