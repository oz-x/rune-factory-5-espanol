"""Reversible replacement of Rune Factory 5 bundle files.

Originals are copied to <game>/es_backup/ before being overwritten, and
es_backup/manifest.json records the SHA-256 of each original and of the file
we wrote. restore() puts a backup back only if the game still has our file;
if Steam replaced it (update or "verify integrity"), the backup is stale and
is discarded without touching the game.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil

from rf5text import BUNDLE_DIR

BACKUP_DIR = 'es_backup'
MANIFEST = 'manifest.json'


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _paths(game: str):
    backup = os.path.join(game, BACKUP_DIR)
    return backup, os.path.join(backup, MANIFEST)


def _read_manifest(game: str) -> dict:
    _, man = _paths(game)
    if not os.path.exists(man):
        return {}
    with open(man, encoding='utf-8') as f:
        return json.load(f)


def _write_manifest(game: str, data: dict) -> None:
    backup, man = _paths(game)
    tmp = man + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, man)


def is_patched(game: str) -> bool:
    return bool(_read_manifest(game))


def restore(game: str) -> list[str]:
    """Undo every replacement. Returns the names of restored files."""
    backup, man = _paths(game)
    done = []
    for name, info in _read_manifest(game).items():
        target = os.path.join(game, BUNDLE_DIR, name)
        saved = os.path.join(backup, name)
        if os.path.exists(target) and os.path.exists(saved) and sha256(target) == info['patched']:
            if sha256(saved) != info['original']:
                raise OSError(f'La copia de seguridad de {name} está dañada.')
            shutil.copyfile(saved, target)
            done.append(name)
        if os.path.exists(saved):
            os.remove(saved)
    if os.path.exists(man):
        os.remove(man)
    if os.path.isdir(backup) and not os.listdir(backup):
        os.rmdir(backup)
    return done


def apply(game: str, files: dict[str, bytes]) -> None:
    """Replace bundle files (name -> new bytes), backing up the originals first.
    On any failure everything already replaced is restored."""
    if is_patched(game):
        raise RuntimeError('restore() first')
    backup, _ = _paths(game)
    os.makedirs(backup, exist_ok=True)
    manifest = {}
    for name, data in files.items():
        target = os.path.join(game, BUNDLE_DIR, name)
        saved = os.path.join(backup, name)
        tmp = target + '.es_tmp'
        try:
            shutil.copyfile(target, saved)
            manifest[name] = {'original': sha256(saved),
                              'patched': hashlib.sha256(data).hexdigest()}
            _write_manifest(game, manifest)  # recorded before the game file changes
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            restore(game)
            raise
