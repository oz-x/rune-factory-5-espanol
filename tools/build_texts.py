"""Regenerates mod/texto/*.json from the translation memory in work/ and the game.

    python tools/build_texts.py "D:/SteamLibrary/steamapps/common/Rune Factory 5"

The game must be unpatched (originals are read). Needs UnityPy and fontTools.
Translation memory (edit a line there, rebuild, reinstall):
    work/tr_guion.json            "en\\x01fr[\\x01M|F]" -> Spanish (script; \\n = structural break)
    work/tr_guion_revgenero.json  same keys, gender-review fixes (take precedence)
    work/tr_tablas.json           "asset\\x02en\\x01fr" -> Spanish (menus, descriptions...)
    work/tr_tablas_revgenero.json same keys, gender-review fixes
    work/tr_glosario.json         "en\\x01fr" -> Spanish (names: items, monsters, places, menus)
    work/tr_singularplural.json   index -> {n2, n3, n4} (item/monster forms used in requests)
    work/tr_apodos.json           index -> [7 nicknames] (PlayerCallingNameTextData)
    work/tr_llamadas.json         English -> Spanish (NPCCallingNameTextData)
    work/correcciones.json        optional manual fixes: {"guion": {TM key: Spanish},
                                  "tablas": {"Asset:path": Spanish}} (final text, applied last)
Output: mod/texto/guion.json   {script: {command: [hash of English, Spanish]}}
        mod/texto/tablas.json  {asset: {path: [hash of English, Spanish]}}
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import rf5patch  # noqa: E402
import rf5text  # noqa: E402
import textproc  # noqa: E402
from rf5unity import LanguageBundles, text_hash  # noqa: E402

WORK = os.path.join(ROOT, 'work')
OUT = os.path.join(ROOT, 'mod', 'texto')
FONT_BUNDLE = '3d75671032be12bec329343fd2eaa14b.bundle'   # holds the Atilla font (ATILN___)
NAME_ASSETS = ('ItemUINameData', 'SkillUINameData', 'RecipeGroupUINameData')
OPTION_CMDS = ('SelectMessage', 'SelectMessageHint', 'FacilityShowlistAdvshop')
PC_FIELDS = ('calling_L', 'called_L', 'calling_M', 'called_M',
             'calling_LX', 'called_LX', 'calling_MX', 'called_MX')


def load(name: str) -> dict:
    path = os.path.join(WORK, name)
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def keep_ws(en: str, es: str) -> str:
    lead = en[:len(en) - len(en.lstrip())]
    trail = en[len(en.rstrip()):]
    return lead + es.strip() + trail


def metrics(game: str) -> textproc.Metrics:
    import UnityPy
    from fontTools.ttLib import TTFont
    env = UnityPy.load(os.path.join(game, rf5text.BUNDLE_DIR, FONT_BUNDLE))
    font = next(o.read() for o in env.objects if o.type.name == 'Font' and o.peek_name() == 'ATILN___')
    tt = TTFont(io.BytesIO(bytes(font.m_FontData)))
    hmtx, upm = tt['hmtx'].metrics, tt['head'].unitsPerEm
    return textproc.Metrics({c: hmtx[g][0] / upm for c, g in tt.getBestCmap().items()}, 1.0)


def max_line(m, s: str) -> float:
    return max((m.line(ln) for ln in s.split('\n')), default=0.0)


def build_script_line(m, cmd: str, en: str, es: str) -> str:
    en_n = en.replace('\r\n', '\n')
    if cmd in OPTION_CMDS:
        out = es.replace('\n', ' ')
    else:
        lines = max(textproc.MSG_LINES, en_n.count('\n') + 1)
        out = textproc.wrap(es.strip(), lines, textproc.TARGET_EM, textproc.MAX_EM, m)[0]
    return keep_ws(en_n, out).replace('\n', '\r\n')


def build_table_line(m, en: str, fr: str, es: str) -> str:
    core, fcore = en.strip(), fr.strip()
    if '\n' not in core and '\n' not in fcore:
        return keep_ws(en, es.replace('\n', ' '))
    base = max(max_line(m, core), max_line(m, fcore))
    lines = max(core.count('\n'), fcore.count('\n')) + 1
    return keep_ws(en, textproc.wrap(es.strip(), lines, base, base * 1.08 + 1, m)[0])


def main() -> None:
    game = sys.argv[1]
    if rf5patch.is_patched(game):
        sys.exit('Desinstala la traducción antes de regenerar (se necesitan los textos originales).')
    m = metrics(game)
    eng, fre = LanguageBundles(game, 'Eng'), LanguageBundles(game, 'Fre')
    fixes = load('correcciones.json')

    tr = load('tr_guion.json')
    tr.update(load('tr_guion_revgenero.json'))
    tr.update(fixes.get('guion', {}))
    guion, missing = {}, 0
    for si, (s_en, s_fr) in enumerate(zip(eng.scripts(), fre.scripts())):
        for ci, name, en in rf5text.script_texts(s_en):
            fr_arg = s_fr[ci][1][rf5text.TEXT_PARAMS[name]]
            key = en + '\x01' + (fr_arg if isinstance(fr_arg, str) else '')
            if name == 'MessagePlayerGender':
                key += '\x01' + ('M' if s_en[ci][1][2] == 1 else 'F')
            if key not in tr:
                missing += re.search('[A-Za-z]', en) is not None
                continue
            guion.setdefault(str(si), {})[str(ci)] = [text_hash(en), build_script_line(m, name, en, tr[key])]

    gl = load('tr_glosario.json')
    tt = load('tr_tablas.json')
    tt.update(load('tr_tablas_revgenero.json'))
    table_fixes = fixes.get('tablas', {})
    sp, apodos, llamadas = load('tr_singularplural.json'), load('tr_apodos.json'), load('tr_llamadas.json')
    fr_tables = fre.tables()
    tablas = {}
    for asset, strings in eng.tables().items():
        out = tablas.setdefault(asset, {})
        frs = fr_tables.get(asset, {})
        for path, en in strings.items():
            fr = frs.get(path, '')
            es = None
            if asset in NAME_ASSETS:
                es = gl.get(en + '\x01' + fr)
                es = keep_ws(en, es) if es else None
            elif asset in ('SystemTextData', 'CutInTextData') and en + '\x01' + fr in gl:
                es = keep_ws(en, gl[en + '\x01' + fr])
            elif asset + '\x02' + en + '\x01' + fr in tt:
                es = build_table_line(m, en, fr, tt[asset + '\x02' + en + '\x01' + fr])
            elif asset == 'SingularPluralDataTable':
                kind, i, field = path.split('/')
                entry = sp.get(str(int(i) + (1000 if kind == 'MonsterNameList' else 0)))
                if entry:
                    es = entry['n' + field[-1]]
            elif asset == 'PlayerCallingNameTextData':
                _, d, field, j = path.split('/')
                names = apodos.get(str(int(d) * 8 + PC_FIELDS.index(field)))
                es = names[int(j)] if names else None
            elif asset == 'NPCCallingNameTextData':
                es = llamadas.get(en)
            es = table_fixes.get(f'{asset}:{path}', es)
            if es and es != en:
                out[path] = [text_hash(en), es]
            elif re.search('[A-Za-z]{3}', en) and not es:
                missing += 1
    os.makedirs(OUT, exist_ok=True)
    for name, data in (('guion.json', guion), ('tablas.json', tablas)):
        with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    n_g = sum(len(v) for v in guion.values())
    n_t = sum(len(v) for v in tablas.values())
    print(f'guion: {n_g} líneas, tablas: {n_t} textos, sin traducción: {missing}')


if __name__ == '__main__':
    main()
