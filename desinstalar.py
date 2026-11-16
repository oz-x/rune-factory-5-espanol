"""Restaura los archivos originales (inglés) de Rune Factory 5.

Uso:  python desinstalar.py ["ruta al juego"]
"""
from __future__ import annotations

import sys

from instalar import InstallError, game_from_args, uninstall


def main() -> None:
    try:
        print(uninstall(game_from_args()))
    except InstallError as e:
        sys.exit(str(e))


if __name__ == '__main__':
    main()
