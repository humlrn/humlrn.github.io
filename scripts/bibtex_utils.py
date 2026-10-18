#!/usr/bin/env python3
"""Small, dependency-free helpers for parsing and writing canonical BibTeX."""
from __future__ import annotations

from collections import OrderedDict
import html
import re
import unicodedata


def normalize_title(value):
    value = re.sub(r"\\[a-zA-Z]+\s*", "", str(value))
    value = unicodedata.normalize("NFKD", html.unescape(value))
    return re.sub(
        r"[^a-z0-9]",
        "",
        "".join(c for c in value if not unicodedata.combining(c)).lower(),
    )


def entry_blocks(source):
    """Read complete BibTeX entries including nested braces and long abstracts."""
    start_re = re.compile(r"@([A-Za-z]+)\s*([({])", re.M)
    i = 0
    while match := start_re.search(source, i):
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        pos = match.end()
        depth = 1
        in_quote = False
        while pos < len(source) and depth:
            char = source[pos]
            if char == '"' and (pos == 0 or source[pos - 1] != "\\"):
                in_quote = not in_quote
            if not in_quote:
                if char == opener:
                    depth += 1
                if char == closer:
                    depth -= 1
            pos += 1
        if depth:
            raise ValueError(f"Unbalanced BibTeX entry beginning at {match.start()}")
        yield match.group(1).lower(), source[match.end() : pos - 1]
        i = pos


def split_top_level(source):
    parts = []
    begin = 0
    depth = 0
    quoted = False
    for i, char in enumerate(source):
        if char == '"' and (not i or source[i - 1] != "\\"):
            quoted = not quoted
        if not quoted:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(source[begin:i].strip())
                begin = i + 1
    parts.append(source[begin:].strip())
    return [part for part in parts if part]


def unwrapped(raw):
    raw = str(raw).strip()
    if len(raw) >= 2 and (raw[0], raw[-1]) in (("{", "}"), ('"', '"')):
        return raw[1:-1]
    return raw


def parse_entries(text):
    result = []
    for entry_type, content in entry_blocks(text):
        pieces = split_top_level(content)
        if not pieces:
            continue
        key = pieces[0].strip()
        if not key or "=" in key:
            continue
        fields = OrderedDict()
        for piece in pieces[1:]:
            pair = re.match(r"^([A-Za-z][\w-]*)\s*=\s*(.*)$", piece, re.S)
            if pair:
                fields[pair.group(1).lower()] = unwrapped(pair.group(2))
        if "title" not in fields:
            continue
        result.append({"type": entry_type, "key": key, "fields": fields})
    return result


def fmt(entry):
    fields = entry["fields"]
    body = ",\n".join(
        f"  {key} = {{{value}}}"
        for key, value in fields.items()
        if value is not None and str(value) != ""
    )
    return f'@{entry["type"]}{{{entry["key"]},\n{body}\n}}\n'
