"""Read and rewrite the text bundles of one language with UnityPy.

Spanish replaces English: the patched bundles are the Eng_* ones, so the game
shows the translation when its system language (launcher) is English.
"""
from __future__ import annotations

import hashlib
import os

import UnityPy

import rf5text

GROUPS = ('Event', 'Master', 'MasterPreload', 'Text')


def text_hash(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:10]


class LanguageBundles:
    """The text bundles of one language (lang = 'Eng', 'Fre', ...)."""

    def __init__(self, game: str, lang: str = 'Eng'):
        self.game = game
        labels = rf5text.label_bundles(game, [f'{lang}_{g}' for g in GROUPS])
        self.bundles = {g: labels[f'{lang}_{g}'] for g in GROUPS}
        if not self.bundles['Event'] or not self.bundles['Master']:
            raise FileNotFoundError(f'No encuentro los textos {lang} en el catálogo del juego.')
        self.envs = {}
        self.dirty = set()

    def env(self, name: str):
        if name not in self.envs:
            # Read into memory: UnityPy would keep the file open and block replacing it.
            with open(os.path.join(self.game, rf5text.BUNDLE_DIR, name), 'rb') as f:
                self.envs[name] = UnityPy.load(f.read())
        return self.envs[name]

    def _objects(self, group: str, type_name: str):
        for name in self.bundles[group]:
            for obj in self.env(name).objects:
                if obj.type.name == type_name:
                    yield name, obj

    # ---------------------------------------------------------- scripts
    def _pack_objects(self):
        _, pack = next(self._objects('Event', 'TextAsset'))
        index = next(o for _, o in self._objects('Master', 'MonoBehaviour')
                     if o.peek_name() == 'AdvIndexData')
        return pack, index

    def scripts(self) -> list[list]:
        pack, index = self._pack_objects()
        data = pack.read_typetree()['m_Script'].encode('utf-8', 'surrogateescape')
        ends = index.read_typetree()['offset']
        return [rf5text.parse_script(c) for c in rf5text.split_pack(data, ends)]

    def set_scripts(self, scripts: list[list]) -> None:
        pack, index = self._pack_objects()
        data, ends = rf5text.join_pack([rf5text.build_script(c) for c in scripts])
        tree = pack.read_typetree()
        tree['m_Script'] = data.decode('utf-8', 'surrogateescape')
        pack.save_typetree(tree)
        tree = index.read_typetree()
        tree['offset'] = ends
        index.save_typetree(tree)
        self.dirty.update(self.bundles['Event'] + self.bundles['Master'])

    # ----------------------------------------------------------- tables
    def _table_objects(self):
        for group, spec in rf5text.TABLES.items():
            for name, obj in self._objects(group, 'MonoBehaviour'):
                asset = obj.peek_name()
                if asset in spec:
                    yield name, asset, obj, spec[asset]

    def tables(self) -> dict[str, dict[str, str]]:
        return {asset: rf5text.table_strings(obj.read_typetree(), paths)
                for _, asset, obj, paths in self._table_objects()}

    def set_tables(self, edits: dict[str, dict[str, str]]) -> None:
        """edits: asset -> {path: new text}."""
        for name, asset, obj, _ in self._table_objects():
            if not edits.get(asset):
                continue
            tree = obj.read_typetree()
            for path, value in edits[asset].items():
                rf5text.set_table_string(tree, path, value)
            obj.save_typetree(tree)
            self.dirty.add(name)

    def saved(self) -> dict[str, bytes]:
        """New bytes of every modified bundle (LZ4, like the originals)."""
        return {name: self.envs[name].file.save(packer='lz4') for name in sorted(self.dirty)}
