"""Line breaks, runtime tags and validation for Rune Factory 5 text.

The game never wraps text: every line break is stored in the string ("\\r\\n"
in event scripts, "\\n" in tables) and an overlong line simply overflows its
box. Message boxes show 3 lines. Western text is drawn with the "Atilla" font;
widths are measured in em with its advance widths. In-game calibration
(1440p): 52 px/em, the message box holds ~40 em; English wraps at ~36 em.

Runtime tags (kept verbatim): _PlayerName_, _ColBlue_..._ColDef_,
_Request_ItemName2_, {0}, <size=..>...</size>, and the gender switches
_GenderPlayer(masc,fem)_ / _GenderChild1(boy,girl)_ (also Child2, Child3, Child)
and _GenderMob(masc,fem)_ (traveller titles, as the French localization uses).
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))

TARGET_EM = 35.5      # preferred width of a message line
MAX_EM = 38.5         # hard limit of a message line
MSG_LINES = 3
SOFT_BREAK_EM = 26.0  # an English message line this wide before a break was wrapped

with open(os.path.join(HERE, 'rf5tokens.json'), encoding='utf-8') as _f:
    _TOKENS = json.load(_f)
GENDER = re.compile(r'_(Gender(?:Player|Child[123]?|Mob))\(([^(),]*),([^()]*)\)_')
TOKEN = re.compile('|'.join(re.escape(t) for t in sorted(_TOKENS, key=len, reverse=True)))
PLACEHOLDER = re.compile(r'\{\d+(?:,[^{}]*)?\}|</?size(?:=\d+)?>')
ANY_TAG = re.compile(r'_[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*_')
HARD_START = tuple('(（【※*＊-—♪・[「<')

_SAMPLE = {'_PlayerName_': 'Ludmilaaa', '_SpouseName_': 'Priscilla', '_Spouse_': 'Priscilla',
           '_ColBlue_': '', '_ColDef_': '', '_DoubleQuotation_': '"',
           '_Request_ItemName2_': 'unas espadas', '_Request_Monster2_': 'monstruos',
           '_Request_Count_': '99', '_Request_OrderNpc_': 'Priscilla'}


class Metrics:
    def __init__(self, widths: dict[int, float], fallback: float = 1.0):
        self.widths = widths
        self.fallback = fallback

    def text(self, s: str) -> float:
        w = self.widths
        return sum(w.get(ord(c), self.fallback) for c in s)

    def line(self, line: str) -> float:
        return self.text(expand(line))


def expand(s: str) -> str:
    """Replace runtime tags by representative text (worst case for gender switches)."""
    s = GENDER.sub(lambda m: max(m.group(2), m.group(3), key=len), s)

    def rep(m):
        t = m.group(0)
        if t in _SAMPLE:
            return _SAMPLE[t]
        if t.startswith(('_Child', '_Called', '_Calling')):
            return 'Nombrexx'
        return t.strip('_')[:10] if t.count('_') == 2 else 'Nombrexxxx'
    s = TOKEN.sub(rep, s)
    return PLACEHOLDER.sub(lambda m: '' if m.group(0).startswith('<') else '9999', s)


def split_hard(en: str, m: Metrics, soft_em: float) -> list[str]:
    """Paragraphs of an English string: joins the lines that were wrapped."""
    lines = en.split('\n')
    paras = [lines[0]]
    for prev, cur in zip(lines, lines[1:]):
        if (m.line(prev) >= soft_em and cur.strip() and not cur.lstrip().startswith(HARD_START)
                and not prev.rstrip().endswith(':')):
            paras[-1] = paras[-1].rstrip() + ' ' + cur.lstrip()
        else:
            paras.append(cur)
    return paras


def _wrap_para(text: str, width: float, m: Metrics) -> list[str]:
    lines, cur = [], ''
    for w in text.split(' '):
        cand = w if not cur else cur + ' ' + w
        if cur and m.line(cand) > width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    lines.append(cur)
    return lines


def wrap(text: str, max_lines: int, base: float, limit: float, m: Metrics) -> tuple[str, bool]:
    """Wrap '\\n'-separated paragraphs at `base` em, widening up to `limit`
    when needed to stay within max_lines. Returns (text, fits)."""
    paras = text.split('\n')
    width = base
    while True:
        out = [ln for p in paras for ln in _wrap_para(p, width, m)]
        if len(out) <= max_lines or width >= limit:
            break
        width = min(width + 0.5, limit)
    if len(out) > 1 and m.line(out[-1]) < 4 and width < limit:   # avoid a lone short word
        wider = [ln for p in paras for ln in _wrap_para(p, min(width + 3, limit), m)]
        if len(wider) < len(out):
            out = wider
    fits = len(out) <= max_lines and all(m.line(ln) <= limit + 0.01 for ln in out)
    return '\n'.join(out), fits


def tags(s: str) -> Counter:
    s = GENDER.sub('', s)
    c = Counter(TOKEN.findall(s))
    c.update(PLACEHOLDER.findall(s))
    return c


def problems(en: str, es: str, allow_gender: bool = True) -> list[str]:
    """Errors that would break the game or the text (empty list = OK)."""
    errs = []
    te, ts = tags(en), tags(es)
    if te != ts:
        errs.append(f'tags differ: missing {dict(te - ts)} extra {dict(ts - te)}')
    unknown = [t for t in ANY_TAG.findall(TOKEN.sub(' ', GENDER.sub(' ', es))) if t not in _TOKENS]
    if unknown:
        errs.append(f'unknown tags {unknown} (keep tags exactly as in the source)')
    for name, a, b in GENDER.findall(es):
        if not allow_gender:
            errs.append('_GenderPlayer(...)_ is not supported here: write a neutral sentence')
            break
        if not a.strip() or not b.strip() or ',' in b:
            errs.append(f'bad gender switch _{name}({a},{b})_: needs exactly "masc,fem"')
    if es.count('(') != es.count(')') and en.count('(') == en.count(')'):
        errs.append('unbalanced parentheses')
    if not es.strip() and en.strip():
        errs.append('empty translation')
    return errs
