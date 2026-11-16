"""Instala la traducción al español de Rune Factory 5 (sustituye el idioma inglés).

Uso:  python instalar.py ["ruta al juego"]
Para volver al inglés original:  python desinstalar.py ["ruta al juego"]
Sin ruta, busca el juego en las bibliotecas de Steam.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# PyInstaller extrae los datos en sys._MEIPASS; en el repositorio están junto al script.
DATA = getattr(sys, '_MEIPASS', HERE)
sys.path.insert(0, os.path.join(HERE, 'tools'))

import rf5patch  # noqa: E402
import rf5text  # noqa: E402
from rf5unity import LanguageBundles, text_hash  # noqa: E402

GAME_FOLDER = 'Rune Factory 5'
TEXT_DIR = os.path.join(DATA, 'mod', 'texto')
MIN_MATCH = 0.7   # below this share of matching lines the game version is too different


class InstallError(Exception):
    pass


def is_game(path: str) -> bool:
    return os.path.isfile(os.path.join(path, rf5text.AA_DIR, 'catalog.json'))


def steam_libraries() -> list[str]:
    roots = []
    try:
        import winreg
        for hive, key, value in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                 (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    roots.append(winreg.QueryValueEx(k, value)[0])
            except OSError:
                pass
    except ImportError:
        pass
    roots.append(r'C:\Program Files (x86)\Steam')
    libs = []
    for root in roots:
        libs.append(root)
        vdf = os.path.join(root, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            with open(vdf, encoding='utf-8', errors='replace') as f:
                libs += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    return list(dict.fromkeys(os.path.normpath(p) for p in libs))


def find_game() -> str | None:
    for lib in steam_libraries():
        path = os.path.join(lib, 'steamapps', 'common', GAME_FOLDER)
        if is_game(path):
            return path
    return None


def _load(name: str) -> dict:
    with open(os.path.join(TEXT_DIR, name), encoding='utf-8') as f:
        return json.load(f)


def _by_hash(groups) -> dict:
    out = {}
    for entries in groups:
        for h, es in entries.values():
            out.setdefault(h, es)
    return out


def _place(entries: dict, current: dict, by_hash: dict, total: list) -> dict:
    """Spanish for each slot whose English is unchanged; lines that moved (game
    update) are found by the hash of their English text.
    entries: slot -> [hash, es]; current: slot -> English in the game."""
    out = {}
    for slot, en in current.items():
        h = text_hash(en)
        hit = entries.get(slot)
        if hit and hit[0] == h:
            out[slot] = hit[1]
        elif h in by_hash:
            out[slot] = by_hash[h]
    total[0] += sum(1 for slot in entries if slot in out)
    total[1] += len(entries)
    return out


def install(game: str) -> str:
    if not is_game(game):
        raise InstallError(f'No encuentro Rune Factory 5 en "{game}".')
    rf5patch.restore(game)
    guion, tablas = _load('guion.json'), _load('tablas.json')
    eng = LanguageBundles(game, 'Eng')
    stats = [0, 0]

    scripts = eng.scripts()
    by_hash = _by_hash(guion.values())
    for si, cmds in enumerate(scripts):
        lines = {str(ci): en for ci, _, en in rf5text.script_texts(cmds)}
        if not lines:
            continue
        for ci, es in _place(guion.get(str(si), {}), lines, by_hash, stats).items():
            op, args = cmds[int(ci)]
            args[rf5text.TEXT_PARAMS[rf5text.COMMANDS[op][0]]] = es
    eng.set_scripts(scripts)

    edits = {}
    for asset, strings in eng.tables().items():
        if asset in tablas:
            edits[asset] = _place(tablas[asset], strings, _by_hash([tablas[asset]]), stats)
    eng.set_tables(edits)

    if stats[1] == 0 or stats[0] / stats[1] < MIN_MATCH:
        raise InstallError('El juego tiene otra versión de los textos; no se ha instalado nada.')
    rf5patch.apply(game, eng.saved())
    return (f'Traducción instalada ({stats[0]} de {stats[1]} textos).\n'
            'En el lanzador del juego, deja "English" como idioma del sistema.')


def uninstall(game: str) -> str:
    if not is_game(game):
        raise InstallError(f'No encuentro Rune Factory 5 en "{game}".')
    restored = rf5patch.restore(game)
    return 'Juego restaurado al original.' if restored else 'No había ninguna traducción instalada.'


def game_from_args() -> str:
    game = sys.argv[1] if len(sys.argv) > 1 else find_game()
    if not game:
        sys.exit('No encuentro el juego. Pasa la carpeta del juego como argumento.')
    return game


def main() -> None:
    try:
        print(install(game_from_args()))
    except InstallError as e:
        sys.exit(str(e))


if __name__ == '__main__':
    main()
