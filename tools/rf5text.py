"""Rune Factory 5 (Steam): where the text lives and how to read/write it.

Text is in Unity Addressables bundles under
    Rune Factory 5_Data/StreamingAssets/aa/StandaloneWindows64/<hash>.bundle
The catalog (StreamingAssets/aa/catalog.json) maps labels to bundles. Each
language has its own labels (Jpn_, Eng_, Fre_, Ger_, Kor_, Chs_, Cht_):
    <Lang>_Event          pack.bytes: every event script (dialogue)
    <Lang>_Master         AdvIndexData (script end offsets in pack.bytes) and
                          UISystemTextData/StringFormatData tables
    <Lang>_MasterPreload  SystemTextData, item names/descriptions
    <Lang>_Text           nicknames, timeline captions, subtitles
Bundle requests carry m_Crc = 0, so the game does not verify bundle contents.

pack.bytes is the concatenation of scripts; AdvIndexData.offset[i] is the end
of script i. A script is:
    i32 command count, then per command: i16 opcode + its parameters
    (i32 for ints, (i32 length incl. NUL, i32 offset) for strings),
    then the UTF-16LE string pool. Offsets are relative to the script start.
Parameter layouts per opcode come from Grimoire (RF5-Research, MIT):
tools/adv_commands.json, with RenameA (571) taking no parameters on Steam.
"""
from __future__ import annotations

import base64
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = 'Rune Factory 5_Data'
AA_DIR = os.path.join(DATA_DIR, 'StreamingAssets', 'aa')
BUNDLE_DIR = os.path.join(AA_DIR, 'StandaloneWindows64')

# Script commands whose string parameter (by index) is shown to the player.
TEXT_PARAMS = {
    'Message': 4,
    'MessageRand': 4,
    'MessagePlayerGender': 5,
    'MessageChildPersonality': 5,
    'SelectMessage': 3,
    'SelectMessageHint': 2,
    'FacilityShowlistAdvshop': 3,
}

# Translatable fields of the MonoBehaviour tables: label -> {asset: [field paths]}.
# A path walks dict keys; '*' expands every element of a list.
TABLES = {
    'Master': {
        'NPCDiscriptData': ['str/*'], 'SkillUIDiscriptData': ['str/*'], 'SkillUINameData': ['str/*'],
        'HUDSubtitleTextData': ['str/*'], 'RecipeGroupUINameData': ['str/*'],
        'RecipeGroupUIDiscriptData': ['str/*'], 'CutInTextData': ['str/*'],
        'MovieSubtitleTextData': ['str/*'],
        'ItemDetailFullText': ['formatData/*/format'], 'ItemParameterTextFormat': ['formatData/*/format'],
        'SingularPluralDataTable': ['ItemNameList/*/ItemName2', 'ItemNameList/*/ItemName3',
                                    'ItemNameList/*/ItemName4', 'MonsterNameList/*/MonsterName2',
                                    'MonsterNameList/*/MonsterName3', 'MonsterNameList/*/MonsterName4'],
    },
    'MasterPreload': {'SystemTextData': ['str/*'], 'ItemUINameData': ['str/*'],
                      'ItemUIDiscriptData': ['str/*']},
    'Text': {
        'NPCCallingNameTextData': ['datas/*/str/*'],
        'PlayerCallingNameTextData': [f'datas/*/{k}/*' for k in (
            'calling_L', 'called_L', 'calling_M', 'called_M',
            'calling_LX', 'calling_MX', 'called_LX', 'called_MX')],
        'TimelineMsgTable': ['text/*'], 'TitleSubtitleTextData': ['str/*'],
        'VoiceSubtitleTextData': ['str/*'],
    },
}


def table_strings(tree: dict, paths: list[str]) -> dict[str, str]:
    """{'path/with/indices': text} for every string selected by `paths`."""
    out = {}

    def walk(node, parts, prefix):
        if not parts:
            if isinstance(node, str):
                out[prefix] = node
            return
        head, rest = parts[0], parts[1:]
        if head == '*':
            for i, child in enumerate(node):
                walk(child, rest, f'{prefix}/{i}' if prefix else str(i))
        elif isinstance(node, dict) and head in node:
            walk(node[head], rest, f'{prefix}/{head}' if prefix else head)

    for p in paths:
        walk(tree, p.split('/'), '')
    return out


def set_table_string(tree: dict, path: str, value: str) -> None:
    node = tree
    parts = path.split('/')
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def _load_commands() -> dict[int, tuple[str, str]]:
    with open(os.path.join(HERE, 'adv_commands.json'), encoding='utf-8-sig') as f:
        cmds = {c['ID']: (c['Name'], ''.join(v[0] for v in c['Params'].values()))
                for c in json.load(f)}
    cmds[571] = ('RenameA', '')
    return cmds


COMMANDS = _load_commands()


# ---------------------------------------------------------------- catalog

def _catalog_object(buf: bytes, off: int):
    kind = buf[off]
    off += 1
    if kind in (0, 1):
        n = struct.unpack_from('<i', buf, off)[0]
        raw = buf[off + 4:off + 4 + n]
        return raw.decode('ascii' if kind == 0 else 'utf-16-le')
    if kind == 4:
        return struct.unpack_from('<i', buf, off)[0]
    return None


def label_bundles(game: str, labels: list[str]) -> dict[str, list[str]]:
    """label -> bundle file names holding the assets with that label."""
    with open(os.path.join(game, AA_DIR, 'catalog.json'), encoding='utf-8') as f:
        cat = json.load(f)
    ids = cat['m_InternalIds']
    kd = base64.b64decode(cat['m_KeyDataString'])
    bd = base64.b64decode(cat['m_BucketDataString'])
    ed = base64.b64decode(cat['m_EntryDataString'])
    buckets, off = [], 4
    for _ in range(struct.unpack_from('<i', bd, 0)[0]):
        koff, n = struct.unpack_from('<ii', bd, off)
        buckets.append((_catalog_object(kd, koff), struct.unpack_from(f'<{n}i', bd, off + 8)))
        off += 8 + 4 * n
    entry = [struct.unpack_from('<7i', ed, 4 + 28 * i)
             for i in range(struct.unpack_from('<i', ed, 0)[0])]
    by_key = {k: e for k, e in buckets}
    out = {}
    for label in labels:
        names = []
        for x in by_key.get(label, ()):
            dep = entry[x][2]
            if dep < 0:
                continue
            for y in buckets[dep][1]:
                name = ids[entry[y][0]].rsplit('/', 1)[-1]
                if name.endswith('.bundle') and name not in names:
                    names.append(name)
        out[label] = names
    return out


# ---------------------------------------------------------------- scripts

def parse_script(data: bytes) -> list[tuple[int, list]]:
    """[(opcode, args)]: int args are ints, string args are str (without NUL)
    or a raw (length, offset) tuple when the length is 0."""
    if not data:
        return []
    count, pos, cmds = struct.unpack_from('<i', data, 0)[0], 4, []
    for _ in range(count):
        op = struct.unpack_from('<h', data, pos)[0]
        pos += 2
        args = []
        for kind in COMMANDS[op][1]:
            if kind == 's':
                length, off = struct.unpack_from('<ii', data, pos)
                pos += 8
                if length > 0:
                    text = data[off:off + 2 * length].decode('utf-16-le')
                    if not text.endswith('\0'):
                        raise ValueError('unterminated string')
                    args.append(text[:-1])
                else:
                    args.append((length, off))
            else:
                args.append(struct.unpack_from('<i', data, pos)[0])
                pos += 4
        cmds.append((op, args))
    return cmds


def build_script(cmds: list[tuple[int, list]]) -> bytes:
    """Inverse of parse_script; strings are pooled in reference order (as the game's tool does)."""
    if not cmds:
        return b''
    head = bytearray(struct.pack('<i', len(cmds)))
    strings = []
    for op, args in cmds:
        head += struct.pack('<h', op)
        for kind, arg in zip(COMMANDS[op][1], args):
            if kind == 's':
                strings.append((len(head), arg))
                head += bytes(8)
            else:
                head += struct.pack('<i', arg)
    pool = bytearray()
    for pos, arg in strings:
        if isinstance(arg, tuple):
            struct.pack_into('<ii', head, pos, *arg)
            continue
        raw = (arg + '\0').encode('utf-16-le')
        struct.pack_into('<ii', head, pos, len(raw) // 2, len(head) + len(pool))
        pool += raw
    return bytes(head + pool)


def split_pack(pack: bytes, ends: list[int]) -> list[bytes]:
    out, start = [], 0
    for end in ends:
        out.append(pack[start:end])
        start = end
    return out


def join_pack(chunks: list[bytes]) -> tuple[bytes, list[int]]:
    ends, pos = [], 0
    for c in chunks:
        pos += len(c)
        ends.append(pos)
    return b''.join(chunks), ends


def script_texts(cmds) -> list[tuple[int, str, str]]:
    """[(command index, command name, text)] for player-visible strings."""
    out = []
    for ci, (op, args) in enumerate(cmds):
        name = COMMANDS[op][0]
        if name in TEXT_PARAMS and isinstance(args[TEXT_PARAMS[name]], str):
            out.append((ci, name, args[TEXT_PARAMS[name]]))
    return out
