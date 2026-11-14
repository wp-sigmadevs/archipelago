#!/usr/bin/env python3
"""Build the "Archipelago Icons" Zed icon theme from the Atom Material Icons
JetBrains plugin (MIT, (c) Elior "Mallowigi" Boukhobza) installed in a JetBrains IDE,
including your own customised associations from that IDE.

Usage: python3 generate_icons.py [path/to/a-file-icon-idea-*.jar]
Writes icons/icons/ and icons/icon_themes/archipelago-icons.json.
"""
import json
import re
import shutil
import sre_constants as C
import sre_parse
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
JB = Path.home() / "Library/Application Support/JetBrains"
OUT_JSON = ROOT / "icons/icon_themes/archipelago-icons.json"
ICONS = ROOT / "icons/icons"

# Extra folder names -> an existing folder name whose icon they reuse
# (names the plugin doesn't cover but are common in WP/Next.js projects).
# Test-file icons (testts, testjs, …) recoloured to one strong green, standing in for
# JetBrains' green Tests file-colour rows, which Zed can't draw.
TEST_GREEN = "6cb463"

FOLDER_ALIASES = {
    "contexts": "context", "configs": "config", "template-parts": "templates",
    "blocks": "components", "block": "components", "kit": "components",
    "webhooks": "hooks", "listeners": "events", "policies": "guards",
}
# Plain closed folders: the plugin's solid folder reads as "empty". Zed can't tell
# empty from non-empty, so draw a folder with paper peeking out (own artwork).
FOLDER_FILLED = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24">'
    '<path fill="#607d8b" d="M10 4H4c-1.1 0-2 .9-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8'
    'a2 2 0 0 0-2-2h-8z"/>'
    '<rect x="5" y="7" width="14" height="7" rx="1" fill="#cfd8dc"/>'
    '<path fill="#78909c" d="M2 11h20v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z"/>'
    '</svg>\n'
)
EXPAND_LIMIT = 200  # max names generated from one regex pattern


# --- inputs ----------------------------------------------------------------------
def newest(paths):
    paths = [p for p in paths if p.exists()]
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def find_jar():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    jar = newest(JB.glob("*/plugins/Atom Material Icons/lib/a-file-icon-idea-*.jar"))
    if not jar:
        sys.exit("Atom Material Icons plugin not found in any JetBrains IDE")
    return jar


def plugin_associations(xml):
    """Default associations shipped with the plugin."""
    for el in ET.fromstring(xml).iter("regex"):
        names = el.get("fileNames") or el.get("folderNames") or ""
        yield {
            "name": el.get("name"),
            "examples": [n.strip() for n in names.split(",") if n.strip()],
            "pattern": el.get("pattern"),
            "icon": el.get("icon"),
            "priority": int(el.get("priority", 0)),
            "color": el.get("iconColor"),
            "folderColor": el.get("folderColor"),
            "folderIconColor": el.get("folderIconColor"),
        }


def user_associations():
    """Associations you customised in the IDE (Settings > Atom Material Icons),
    from the most recently changed JetBrains IDE config."""
    out = {"file": [], "folder": []}
    cfg = newest(JB.glob("*/options/atom-icon-associations.xml"))
    if not cfg:
        return out
    for lst in ET.parse(cfg).getroot().iter("option"):
        kind = {"selectedFileAssociations": "file",
                "selectedFolderAssociations": "folder"}.get(lst.get("name"))
        if not kind:
            continue
        for el in lst.iter():
            o = {x.get("name"): x.get("value") for x in el.findall("option")
                 if x.get("value") is not None}
            if "pattern" in o and o.get("icon") and o.get("enabled", "true") != "false":
                out[kind].append({
                    "name": o.get("name"), "examples": [], "pattern": o["pattern"],
                    "icon": o["icon"], "priority": int(o.get("priority", 100)),
                    "color": o.get("iconColor"), "folderColor": o.get("folderColor"),
                    "folderIconColor": o.get("folderIconColor"),
                })
    print(f"user overrides from {cfg}: {len(out['file'])} file, {len(out['folder'])} folder")
    return out


def merged(defaults, overrides):
    """User entries replace plugin entries of the same name (keeping its examples)."""
    by_name = {a["name"]: a for a in defaults}
    for u in overrides:
        base = by_name.get(u["name"], {})
        by_name[u["name"]] = {**base, **{k: v for k, v in u.items() if v not in (None, [])}}
    return list(by_name.values())


# --- regex -> concrete names -------------------------------------------------------
def enumerate_regex(pattern):
    """All strings a regex matches, or None if infinite/too many/unsupported."""
    try:
        tree = sre_parse.parse(pattern)
    except Exception:
        return None

    def seq(items):
        out = [""]
        for op, av in items:
            alts = node(op, av)
            if alts is None:
                return None
            out = [a + b for a in out for b in alts]
            if len(out) > EXPAND_LIMIT:
                return None
        return out

    def node(op, av):
        if op is C.LITERAL:
            return [chr(av)]
        if op is C.AT:
            return [""]
        if op is C.SUBPATTERN:
            return seq(av[-1])
        if op is C.BRANCH:
            out = []
            for b in av[1]:
                r = seq(b)
                if r is None:
                    return None
                out += r
            return out
        if op is C.IN:
            chars = []
            for o, a in av:
                if o is C.LITERAL:
                    chars.append(chr(a))
                elif o is C.RANGE and a[1] - a[0] < 12:
                    chars += [chr(c) for c in range(a[0], a[1] + 1)]
                else:
                    return None
            return chars
        if op in (C.MAX_REPEAT, C.MIN_REPEAT):
            lo, hi, body = av
            if hi > 3:
                return None
            one = seq(body)
            if one is None:
                return None
            out, cur = [], [""]
            for i in range(hi + 1):
                if i >= lo:
                    out += cur
                cur = [a + b for a in cur for b in one]
            return out
        return None  # ANY, CATEGORY, NOT_LITERAL, ...

    names = seq(tree)
    return sorted(set(names)) if names else None


def targets_from_pattern(pattern, is_folder):
    """('suffix'|'name', value) pairs a pattern stands for."""
    if not pattern or "/" in pattern:
        return []
    p = pattern[1:] if pattern.startswith("^") else pattern
    if not is_folder and p.startswith(r".*\."):
        return [("suffix", s) for s in enumerate_regex(p[4:]) or [] if s]
    if p.startswith(".*") or p.startswith("(?"):
        return []
    return [("name", n) for n in enumerate_regex(p) or [] if n and n not in (".", "_")]


# --- svg ----------------------------------------------------------------------------
def recolor(svg, marks):
    """Apply colours the way the plugin does at runtime: to elements carrying
    data-iconColor / data-folderColor / data-folderIconColor."""
    for mark, colour in marks.items():
        if colour:
            svg = re.sub(rf"<[^>]*{mark}=[^>]*>",
                         lambda m: re.sub(r'fill="#[0-9a-fA-F]{3,8}"',
                                          f'fill="#{colour.lower()}"', m.group(0)), svg)
    return svg


def case_variants(name):
    """The plugin matches case-insensitively; Zed doesn't. Add the common
    spellings: as written, BASE.ext upper-cased, Base.ext capitalised."""
    base, dot, ext = name.partition(".") if not name.startswith(".") else (name, "", "")
    return {name, base.upper() + dot + ext, base[:1].upper() + base[1:] + dot + ext}


def best(mapping, key, value, priority):
    """Keep the highest-priority association per key (plugin semantics)."""
    if key not in mapping or priority > mapping[key][1]:
        mapping[key] = (value, priority)


# --- build --------------------------------------------------------------------------
def main():
    jar = find_jar()
    user = user_associations()
    with zipfile.ZipFile(jar) as z:
        members = set(z.namelist())

        def read(p):
            return z.read(p).decode()

        files = merged(plugin_associations(z.read("iconGenerator/icon_associations.xml")),
                       user["file"])
        folders = merged(plugin_associations(z.read("iconGenerator/folder_associations.xml")),
                         user["folder"])

        # files: key = (svg stem, colour)
        suffixes, stems = {}, {}
        for a in files:
            if not a.get("icon") or "assets" + a["icon"] not in members:
                continue
            key = (Path(a["icon"]).stem, (a.get("color") or "").lower())
            for n in a["examples"]:
                if n.startswith("*."):
                    best(suffixes, n[2:], key, a["priority"])
                elif "*" not in n:
                    for v in case_variants(n):
                        best(stems, v, key, a["priority"])
            for kind, v in targets_from_pattern(a.get("pattern"), False):
                for w in (case_variants(v) if kind == "name" else [v]):
                    best(suffixes if kind == "suffix" else stems, w, key, a["priority"])
        # Dotfiles (".env") have no extension for Zed, only a name: map them too.
        for suffix, entry in list(suffixes.items()):
            stems.setdefault("." + suffix, entry)

        # folders: key = (svg stem, folderColor, folderIconColor)
        dirs = {}
        for a in folders:
            stem = Path(a.get("icon") or "").stem
            if not stem or f"assets/icons/folders/{stem}.svg" not in members:
                continue
            key = (stem, (a.get("folderColor") or "").lower(),
                   (a.get("folderIconColor") or "").lower())
            names = [n for n in a["examples"] if "*" not in n]
            names += [v for _, v in targets_from_pattern(a.get("pattern"), True)]
            for n in names:
                for v in case_variants(n):
                    best(dirs, v, key, a["priority"])

        shutil.rmtree(ICONS, ignore_errors=True)

        def write(rel, svg):
            out = ICONS / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg)
            return f"./icons/{rel}"

        def tint(key):
            return (key[0], TEST_GREEN) if key[0].startswith("test") else key

        def ref(key):
            key = tint(key)
            return f"{key[0]}-{key[1]}" if key[1] else key[0]

        file_icons = {}
        keys = {v for v, _ in suffixes.values()} | {v for v, _ in stems.values()} | {("file", "")}
        for key in sorted(keys):
            svg = recolor(read(f"assets/icons/files/{key[0]}.svg"), {"data-iconColor": tint(key)[1]})
            file_icons[ref(key)] = {"path": write(f"files/{ref(key)}.svg", svg)}
        file_icons["default"] = file_icons["file"]

        folder_cache = {}

        def folder_pair(key):
            if key not in folder_cache:
                stem, fc, fic = key
                name = "-".join(x for x in key if x)
                marks = {"data-folderColor": fc, "data-folderIconColor": fic}
                closed = recolor(read(f"assets/icons/folders/{stem}.svg"), marks)
                pair = {"collapsed": write(f"folders/{name}.svg", closed)}
                opened = f"assets/icons/foldersOpen/{stem}.svg"
                pair["expanded"] = (write(f"foldersOpen/{name}.svg", recolor(read(opened), marks))
                                    if opened in members else pair["collapsed"])
                folder_cache[key] = pair
            return folder_cache[key]

        named_dirs = {n: folder_pair(k) for n, (k, _) in dirs.items()}
        for alias, target in FOLDER_ALIASES.items():
            if alias not in named_dirs and target in named_dirs:
                named_dirs[alias] = named_dirs[target]
        default_dir = {"collapsed": write("folders/folder-filled.svg", FOLDER_FILLED),
                       "expanded": folder_pair(("folder", "", ""))["expanded"]}

    theme = {
        "$schema": "https://zed.dev/schema/icon_themes/v0.3.0.json",
        "name": "Archipelago Icons",
        "author": "Icons: Atom Material Icons by Elior Boukhobza (MIT)",
        "themes": [{
            "name": "Archipelago Icons",
            "appearance": "dark",
            "directory_icons": default_dir,
            "named_directory_icons": dict(sorted(named_dirs.items())),
            "file_stems": {k: ref(v) for k, (v, _) in sorted(stems.items())},
            "file_suffixes": {k: ref(v) for k, (v, _) in sorted(suffixes.items())},
            "file_icons": file_icons,
        }],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(theme, indent=2) + "\n")
    print(f"wrote {OUT_JSON}: {len(suffixes)} suffixes, {len(stems)} file names, "
          f"{len(named_dirs)} folders, {len(file_icons)} file icons")


if __name__ == "__main__":
    main()
