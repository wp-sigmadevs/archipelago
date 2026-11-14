#!/usr/bin/env python3
"""Build the "Archipelago Icons" Zed icon theme from the Atom Material Icons
JetBrains plugin (MIT, (c) Elior "Mallowigi" Boukhobza) installed in PhpStorm.

Usage: python3 generate_icons.py [path/to/a-file-icon-idea-*.jar]
Writes icons/ and icon_themes/archipelago-icons.json. Only icons referenced by
the theme are copied.
"""
import json
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
PLUGIN_LIB = (Path.home() / "Library/Application Support/JetBrains/PhpStorm2026.2"
              / "plugins/Atom Material Icons/lib")
OUT_JSON = ROOT / "icons/icon_themes/archipelago-icons.json"
ICONS = ROOT / "icons/icons"


def find_jar():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    jars = sorted(PLUGIN_LIB.glob("a-file-icon-idea-*.jar"))
    if not jars:
        sys.exit(f"Atom Material Icons jar not found in {PLUGIN_LIB}")
    return jars[-1]


def associations(z, name):
    """(names, icon, priority) per <regex>, from the plugin's association XML."""
    root = ET.fromstring(z.read(f"iconGenerator/{name}"))
    for el in root.iter():
        names = el.get("fileNames") or el.get("folderNames")
        if el.tag == "regex" and names and el.get("icon"):
            yield ([n.strip() for n in names.split(",") if n.strip()],
                   el.get("icon"), int(el.get("priority", 0)))


def best(mapping, key, value, priority):
    """Keep the highest-priority association per key (plugin semantics)."""
    if key not in mapping or priority > mapping[key][1]:
        mapping[key] = (value, priority)


def main():
    jar = find_jar()
    with zipfile.ZipFile(jar) as z:
        members = set(z.namelist())
        suffixes, stems, folders = {}, {}, {}

        for names, icon, prio in associations(z, "icon_associations.xml"):
            path = "assets" + icon  # /icons/files/php.svg -> assets/icons/files/php.svg
            if path not in members:
                continue
            key = Path(icon).stem
            for n in names:
                if n.startswith("*."):
                    best(suffixes, n[2:], key, prio)
                elif "*" not in n:
                    best(stems, n, key, prio)

        # Dotfiles (".env") have no extension for Zed, only a name: map them too.
        for suffix, entry in list(suffixes.items()):
            stems.setdefault("." + suffix, entry)

        for names, icon, prio in associations(z, "folder_associations.xml"):
            name = icon.lstrip("/")
            if f"assets/icons/folders/{name}" not in members:
                continue
            for n in names:
                if "*" not in n:
                    best(folders, n, Path(name).stem, prio)

        # Fresh copy of only the icons we reference.
        shutil.rmtree(ICONS, ignore_errors=True)
        file_keys = {v for v, _ in suffixes.values()} | {v for v, _ in stems.values()} | {"file"}

        def copy(src, dst):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(src))

        file_icons = {}
        for key in sorted(file_keys):
            copy(f"assets/icons/files/{key}.svg", ICONS / f"files/{key}.svg")
            file_icons[key] = {"path": f"./icons/files/{key}.svg"}
        file_icons["default"] = file_icons["file"]

        def folder_pair(stem):
            closed = f"assets/icons/folders/{stem}.svg"
            opened = f"assets/icons/foldersOpen/{stem}.svg"
            copy(closed, ICONS / f"folders/{stem}.svg")
            pair = {"collapsed": f"./icons/folders/{stem}.svg"}
            if opened in members:
                copy(opened, ICONS / f"foldersOpen/{stem}.svg")
                pair["expanded"] = f"./icons/foldersOpen/{stem}.svg"
            else:
                pair["expanded"] = pair["collapsed"]
            return pair

        named_dirs = {n: folder_pair(stem) for n, (stem, _) in sorted(folders.items())}
        default_dir = folder_pair("folder")
        # Plain folders: the plugin's closed folder is solid (reads as "empty");
        # PhpStorm shows an outline. Draw a closed outline matching the plugin's
        # open-folder outline (own artwork, same colour).
        outline = ICONS / "folders/folder-outline.svg"
        outline.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24">'
            '<path fill="none" stroke="#78909c" stroke-width="2" stroke-linejoin="round" '
            'd="M10 5H4.2C3.5 5 3 5.5 3 6.2v11.6c0 .7.5 1.2 1.2 1.2h15.6c.7 0 1.2-.5 1.2-1.2V8.2'
            'c0-.7-.5-1.2-1.2-1.2H12z"/></svg>\n')
        default_dir["collapsed"] = "./icons/folders/folder-outline.svg"

    theme = {
        "$schema": "https://zed.dev/schema/icon_themes/v0.3.0.json",
        "name": "Archipelago Icons",
        "author": "Icons: Atom Material Icons by Elior Boukhobza (MIT)",
        "themes": [{
            "name": "Archipelago Icons",
            "appearance": "dark",
            "directory_icons": default_dir,
            "named_directory_icons": named_dirs,
            "file_stems": {k: v for k, (v, _) in sorted(stems.items())},
            "file_suffixes": {k: v for k, (v, _) in sorted(suffixes.items())},
            "file_icons": file_icons,
        }],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(theme, indent=2) + "\n")
    print(f"wrote {OUT_JSON}: {len(suffixes)} suffixes, {len(stems)} file names, "
          f"{len(named_dirs)} folders, {len(file_icons)} file icons")


if __name__ == "__main__":
    main()
