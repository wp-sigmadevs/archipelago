#!/usr/bin/env python3
"""Build a Zed theme from PhpStorm's active editor scheme (.icls) + the Islands Dark UI theme.

Usage: python3 generate.py [path/to/scheme.icls]
Re-run after changing colours in PhpStorm.
"""
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

HOME = Path.home()
ICLS = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    HOME / "Library/Application Support/JetBrains/PhpStorm2026.2/colors/_@user_One Dark.icls")
IDE_JAR = Path("/Applications/PhpStorm.app/Contents/lib/intellij.platform.ide.impl.jar")
ISLANDS = "themes/islands/ManyIslandsDark.theme.json"
OUT = Path(__file__).parent / "theme/themes/archipelago.json"

# --- PhpStorm editor scheme -------------------------------------------------
root = ET.parse(ICLS).getroot()
colors = {o.get("name"): o.get("value") for o in root.find("colors")}
attrs = {o.get("name"): o for o in root.find("attributes")}


def attr(*names):
    """First defined attribute among names, following baseAttributes links."""
    for name in names:
        seen = set()
        while name in attrs and name not in seen:
            seen.add(name)
            o = attrs[name]
            if o.get("baseAttributes"):
                name = o.get("baseAttributes")
                continue
            v = o.find("value")
            d = {x.get("name"): x.get("value") for x in (v if v is not None else [])}
            if d:
                return d
            break
    return {}


def hexc(v, alpha=""):
    return None if not v else "#" + v.lower().rjust(6, "0") + alpha


def fg(*names):
    return hexc(attr(*names).get("FOREGROUND"))


def bg(*names):
    return hexc(attr(*names).get("BACKGROUND"))


TEXT_FG, EDITOR_BG = fg("TEXT"), bg("TEXT")


def tok(*names):
    """Zed syntax style from IntelliJ attributes (FONT_TYPE bit 1 = bold, bit 2 = italic)."""
    a = attr(*names)
    s = {"color": hexc(a.get("FOREGROUND")) or TEXT_FG}
    ft = int(a.get("FONT_TYPE", 0))
    if ft & 2:
        s["font_style"] = "italic"
    if ft & 1:
        s["font_weight"] = 700
    return s


# --- Islands Dark UI palette (read from the installed PhpStorm) --------------
with zipfile.ZipFile(IDE_JAR) as z:
    ui = json.loads(z.read(ISLANDS))["colors"]


def u(key, depth=0):
    v = ui[key]
    return u(v, depth + 1) if v in ui and depth < 8 else v.lower()


# --- Syntax ------------------------------------------------------------------
# Zed syntax colours are global, not per language, so build two variants:
# PHP-tuned (your PHP_* customisations) and JS/TS-tuned (WebStorm defaults).
common = {
    "attribute": tok("HTML_ATTRIBUTE_NAME"),
    "boolean": tok("JSON.KEYWORD", "DEFAULT_CONSTANT"),
    "comment": tok("DEFAULT_LINE_COMMENT"),
    "comment.doc": tok("DEFAULT_DOC_COMMENT"),
    "constant": tok("DEFAULT_CONSTANT"),
    "constant.builtin": tok("DEFAULT_CONSTANT"),
    "constructor": tok("DEFAULT_CLASS_NAME"),
    "embedded": tok("TEXT"),
    "emphasis": {"color": TEXT_FG, "font_style": "italic"},
    "emphasis.strong": {"color": TEXT_FG, "font_weight": 700},
    "enum": tok("DEFAULT_CLASS_NAME"),
    "function": tok("DEFAULT_FUNCTION_DECLARATION"),
    "function.method": tok("DEFAULT_INSTANCE_METHOD", "DEFAULT_FUNCTION_CALL"),
    "function.builtin": tok("DEFAULT_FUNCTION_CALL"),
    "hint": tok("INLAY_DEFAULT"),
    "keyword": tok("DEFAULT_KEYWORD"),
    "label": tok("DEFAULT_LABEL"),
    "link_text": tok("HYPERLINK_ATTRIBUTES"),
    "link_uri": tok("HYPERLINK_ATTRIBUTES"),
    "namespace": tok("TS.MODULE_NAME", "DEFAULT_CLASS_NAME"),
    "number": tok("DEFAULT_NUMBER"),
    "operator": tok("DEFAULT_OPERATION_SIGN"),
    "predictive": {"color": fg("DEFAULT_LINE_COMMENT"), "font_style": "italic"},
    "preproc": tok("DEFAULT_KEYWORD"),
    "primary": tok("TEXT"),
    "property": tok("DEFAULT_INSTANCE_FIELD"),
    "punctuation": tok("DEFAULT_BRACES"),
    "punctuation.bracket": tok("DEFAULT_BRACES"),
    "punctuation.delimiter": tok("DEFAULT_COMMA"),
    "punctuation.list_marker": tok("DEFAULT_KEYWORD"),
    "punctuation.markup": tok("DEFAULT_KEYWORD"),
    "punctuation.special": tok("DEFAULT_VALID_STRING_ESCAPE"),
    "selector": tok("CSS.TAG_NAME"),
    "selector.pseudo": tok("CSS.KEYWORD"),
    "string": tok("DEFAULT_STRING"),
    "string.escape": tok("DEFAULT_VALID_STRING_ESCAPE"),
    "string.regex": tok("JS.REGEXP"),
    "string.special": tok("DEFAULT_VALID_STRING_ESCAPE"),
    "string.special.symbol": tok("DEFAULT_CONSTANT"),
    "tag": tok("HTML_TAG_NAME"),
    "text.literal": tok("MARKDOWN_CODE_SPAN", "DEFAULT_STRING"),
    "title": tok("MARKDOWN_HEADER_LEVEL_1"),
    "type": tok("DEFAULT_CLASS_NAME"),
    "type.builtin": tok("DEFAULT_KEYWORD"),
    "variable": tok("DEFAULT_LOCAL_VARIABLE"),
    "variable.builtin": tok("DEFAULT_KEYWORD"),
    "variable.parameter": tok("DEFAULT_PARAMETER"),
    "variable.special": tok("DEFAULT_KEYWORD"),
    "variant": tok("DEFAULT_CONSTANT"),
    "diff.plus": {"color": fg("CONSOLE_GREEN_OUTPUT")},
    "diff.minus": {"color": fg("CONSOLE_RED_OUTPUT")},
    # JS/TS semantic-token styles (WebStorm look). Referenced by name from
    # settings.json "semantic_token_rules" ("style": ["ts.function"]), so the
    # colours live in the theme. No tree-sitter grammar uses these names.
    "ts.variable.local": tok("PHP_VAR"),
    "ts.variable": tok("JS.GLOBAL_VARIABLE"),
    "ts.parameter": tok("DEFAULT_PARAMETER"),
    "ts.property": tok("DEFAULT_INSTANCE_FIELD"),
    "ts.function": tok("JS.GLOBAL_FUNCTION"),
    "ts.type": tok("DEFAULT_CLASS_NAME"),
    "ts.enum_member": tok("DEFAULT_CONSTANT"),
    # CSS/SCSS-only captures (Zed's CSS grammar), coloured like PhpStorm's SCSS.
    "selector.class": tok("SASS_CLASS_NAME", "CSS.CLASS_NAME"),
    "selector.id": tok("CSS.HASH"),
    "selector.pseudo": tok("CSS.PSEUDO"),
    "type.unit": tok("SASS_NUMBER", "CSS.NUMBER"),
    "variable.other.member": tok("SASS_VARIABLE"),  # SCSS $vars (scss extension capture)
    "string.special": tok("CSS.COLOR"),
}
php = {
    **common,
    "keyword": tok("PHP_KEYWORD"),
    "variable": tok("PHP_VAR"),
    "variable.parameter": tok("PHP_PARAMETER"),
    "variable.builtin": tok("PHP_THIS_VAR"),
    "function": tok("PHP_FUNCTION_CALL"),
    "function.method": tok("PHP_INSTANCE_METHOD", "PHP_FUNCTION_CALL"),
    "function.builtin": tok("PHP_PREDEFINED SYMBOL"),
    "property": tok("PHP_INSTANCE_FIELD"),
    "namespace": tok("PHP_IDENTIFIER"),
    "constructor": tok("PHP_CLASS"),
    "type": tok("PHP_CLASS"),
    "constant": tok("PHP_CONSTANT"),
}
js = {
    **common,
    "variable": tok("JS.LOCAL_VARIABLE"),
    "variable.parameter": tok("JS.PARAMETER", "DEFAULT_PARAMETER"),
    "function": tok("JS.GLOBAL_FUNCTION"),
    "function.method": tok("JS.INSTANCE_MEMBER_FUNCTION", "DEFAULT_FUNCTION_CALL"),
    "type.builtin": tok("JS.PRIMITIVE.TYPE", "DEFAULT_KEYWORD"),
    "property": tok("JS.INSTANCE_MEMBER_VARIABLE", "DEFAULT_INSTANCE_FIELD"),
}


# --- UI ----------------------------------------------------------------------
def c(key, alpha=""):
    return hexc(colors.get(key), alpha)


def status(name, fore, back, border):
    return {name: fore, f"{name}.background": back, f"{name}.border": border}


ansi = {n: fg(f"CONSOLE_{n.upper()}_OUTPUT") for n in
        ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")}
caret, selection = c("CARET_COLOR"), c("SELECTION_BACKGROUND")
others = [fg(f"CONSOLE_{n}_OUTPUT") for n in ("BLUE", "MAGENTA", "GREEN", "YELLOW", "CYAN", "RED")]

style = {
    # Window chrome (Islands: frame = main-window-bg, tool windows = tool-window-bg)
    "background": u("main-window-bg"),
    "title_bar.background": u("main-window-bg"),
    "title_bar.inactive_background": u("main-window-bg"),
    "status_bar.background": u("main-window-bg"),
    "panel.background": u("tool-window-bg"),
    "panel.focused_border": None,
    "panel.indent_guide": u("tree-indent-guide-border"),
    "panel.indent_guide_active": u("layer-2-border-inline"),
    "panel.indent_guide_hover": u("layer-2-border-inline"),
    "pane.focused_border": None,
    "surface.background": u("tool-window-bg"),
    "elevated_surface.background": u("popup-bg"),
    "border": u("main-window-bg"),
    "border.variant": u("layer-1-border"),
    "border.focused": u("accent-brand-border-secondary"),
    "border.selected": u("tab-selected-border-active"),
    "border.transparent": "#00000000",
    "border.disabled": u("control-border-disabled"),
    "element.background": u("control-bg"),
    "element.hover": u("toolbar-bg-hovered"),
    "element.active": u("toolbar-bg-pressed"),
    "element.selected": u("selection-bg-active"),
    "element.disabled": u("control-bg-disabled"),
    "ghost_element.background": "#00000000",
    "ghost_element.hover": u("toolbar-bg-hovered"),
    "ghost_element.active": u("toolbar-bg-pressed"),
    "ghost_element.selected": u("selection-bg-active"),
    "ghost_element.disabled": "#00000000",
    "drop_target.background": "#3671e580",
    "text": u("text-default"),
    "text.muted": u("text-muted"),
    "text.placeholder": u("text-secondary"),
    "text.disabled": u("text-disabled"),
    "text.accent": u("text-link"),
    "icon": u("icon-default-stroke"),
    "icon.muted": u("text-muted"),
    "icon.disabled": u("text-disabled"),
    "icon.placeholder": u("text-secondary"),
    "icon.accent": u("popup-completion-match-text"),
    "link_text.hover": u("text-link"),
    "scrollbar.thumb.background": u("toolbar-border"),
    "scrollbar.thumb.hover_background": u("control-border-over-accent"),
    "scrollbar.thumb.border": "#00000000",
    "scrollbar.track.background": "#00000000",
    "scrollbar.track.border": "#00000000",
    # Editor island (colours from your scheme)
    "toolbar.background": EDITOR_BG,
    "tab_bar.background": EDITOR_BG,
    "tab.inactive_background": EDITOR_BG,
    "tab.active_background": u("tab-selected-bg-active"),
    "editor.background": EDITOR_BG,
    "editor.foreground": TEXT_FG,
    "editor.gutter.background": c("GUTTER_BACKGROUND") or EDITOR_BG,
    "editor.subheader.background": c("DIFF_SEPARATORS_BACKGROUND"),
    "editor.active_line.background": c("CARET_ROW_COLOR"),
    "editor.highlighted_line.background": c("CARET_ROW_COLOR"),
    "editor.line_number": c("LINE_NUMBERS_COLOR"),
    "editor.active_line_number": c("LINE_NUMBER_ON_CARET_ROW_COLOR"),
    "editor.hover_line_number": c("LINE_NUMBER_ON_CARET_ROW_COLOR"),
    "editor.invisible": c("WHITESPACES"),
    "editor.wrap_guide": c("RIGHT_MARGIN_COLOR"),
    "editor.active_wrap_guide": c("RIGHT_MARGIN_COLOR"),
    "editor.indent_guide": c("INDENT_GUIDE"),
    "editor.indent_guide_active": c("SELECTED_INDENT_GUIDE"),
    "editor.document_highlight.read_background": bg("IDENTIFIER_UNDER_CARET_ATTRIBUTES"),
    "editor.document_highlight.write_background": bg("WRITE_IDENTIFIER_UNDER_CARET_ATTRIBUTES"),
    "editor.document_highlight.bracket_background": bg("MATCHED_BRACE_ATTRIBUTES"),
    "search.match_background": bg("TEXT_SEARCH_RESULT_ATTRIBUTES"),
    "search.active_match_background": hexc(attr("SEARCH_RESULT_ATTRIBUTES").get("EFFECT_COLOR"), "66"),
    # Terminal (console colours from your scheme)
    "terminal.background": EDITOR_BG,
    "terminal.foreground": fg("CONSOLE_NORMAL_OUTPUT"),
    "terminal.bright_foreground": u("text-default"),
    "terminal.dim_foreground": fg("CONSOLE_GRAY_OUTPUT"),
    **{f"terminal.ansi.{n}": v for n, v in ansi.items()},
    **{f"terminal.ansi.bright_{n}": v for n, v in ansi.items()},
    "terminal.ansi.bright_black": fg("CONSOLE_DARKGRAY_OUTPUT"),
    # Version control: gutter marks from scheme, file status from FILESTATUS_*
    "version_control.added": c("ADDED_LINES_COLOR"),
    "version_control.modified": c("MODIFIED_LINES_COLOR"),
    "version_control.deleted": c("DELETED_LINES_COLOR"),
    "version_control.word_added": c("ADDED_LINES_COLOR", "33"),
    "version_control.word_deleted": c("DELETED_LINES_COLOR", "33"),
    "version_control.conflict_marker.ours": bg("DIFF_INSERTED"),
    "version_control.conflict_marker.theirs": bg("DIFF_MODIFIED"),
    **status("created", c("FILESTATUS_ADDED"), bg("DIFF_INSERTED"), c("FILESTATUS_ADDED")),
    **status("modified", c("FILESTATUS_MODIFIED"), bg("DIFF_MODIFIED"), c("FILESTATUS_MODIFIED")),
    **status("deleted", c("FILESTATUS_DELETED"), bg("DIFF_DELETED"), c("FILESTATUS_DELETED")),
    **status("renamed", c("FILESTATUS_MODIFIED"), bg("DIFF_MODIFIED"), c("FILESTATUS_MODIFIED")),
    **status("conflict", fg("CONSOLE_RED_OUTPUT"), bg("DIFF_CONFLICT"), fg("CONSOLE_RED_OUTPUT")),
    **status("ignored", c("FILESTATUS_SUPPRESSED"), None, None),
    **status("hidden", u("text-disabled"), None, None),
    # Diagnostics: underline colours from scheme, panels from Islands feedback palette
    **status("error", hexc(attr("ERRORS_ATTRIBUTES").get("EFFECT_COLOR")), u("feedback-error-bg"), u("feedback-error-border")),
    **status("warning", hexc(attr("WARNING_ATTRIBUTES").get("EFFECT_COLOR")), u("feedback-warning-bg"), u("feedback-warning-border")),
    **status("info", hexc(attr("INFO_ATTRIBUTES").get("EFFECT_COLOR")), u("feedback-brand-bg"), u("feedback-brand-border")),
    **status("hint", fg("INLAY_DEFAULT"), bg("INLAY_DEFAULT"), bg("INLAY_DEFAULT")),
    **status("success", u("text-success"), u("feedback-success-bg"), u("feedback-success-border")),
    **status("predictive", fg("DEFAULT_LINE_COMMENT"), None, None),
    **status("unreachable", fg("DEFAULT_LINE_COMMENT"), None, None),
    # Rainbow brackets by depth (Zed: "colorize_brackets": true). Sampled from the
    # Rainbow Brackets plugin in PhpStorm; its colours are not stored in the scheme.
    "accents": ["#ffd152", "#6cb463", "#50a8ff", "#e2a5b8"],
    "players": [{"cursor": caret, "background": caret, "selection": selection}]
    + [{"cursor": a, "background": a, "selection": a + "3d"} for a in others],
}
# Drop unset colours, but keep explicit nulls for focus borders (Islands has none).
style = {k: v for k, v in style.items() if v is not None or k.endswith("focused_border")}


def variant(name, syntax):
    return {"name": name, "appearance": "dark", "style": {**style, "syntax": syntax}}


# --- Driftwood: refined take on the PHP variant -----------------------------
# 1. readable teal for calls  2. cool properties to split the warm cluster
# 3. italics on keywords only  4. One Dark-tinted chrome  5. calmer gold  6. brighter comments
COMMENT = "#6b7280"
ember_syntax = {
    k: {kk: vv for kk, vv in v.items() if kk != "font_style" or k in ("keyword", "property")}
    for k, v in php.items()
}
ember_syntax.update({
    "function": {"color": "#4fb3be"},
    "function.method": {"color": "#4fb3be"},
    "property": {**tok("SASS_PROPERTY_NAME"), "font_style": "italic"},
    "variable.builtin": {"color": "#d4886a"},
    "hint": {"color": "#7f8794"},
    "comment": {"color": COMMENT},
    "comment.doc": {"color": COMMENT},
    "predictive": {"color": COMMENT, "font_style": "italic"},
})
ember_style = {**style, **{
    "background": "#21252b",
    "title_bar.background": "#21252b",
    "title_bar.inactive_background": "#21252b",
    "status_bar.background": "#21252b",
    "border": "#21252b",
    "border.variant": "#2c313a",
    "panel.background": "#1e2227",
    "surface.background": "#1e2227",
    "element.background": "#1e2227",
    "element.disabled": "#1e2227",
    "elevated_surface.background": "#2c313a",
    # Inlay hints: WebStorm pill (needs "inlay_hints": {"show_background": true})
    "hint": "#7f8794",
    "hint.background": "#363c44",
    "accents": ["#d8b860", *style["accents"][1:]],
}}

theme = {
    "$schema": "https://zed.dev/schema/themes/v0.2.0.json",
    "name": "Archipelago",
    "author": "Archipelago",
    "themes": [variant("Archipelago Classic", php),
               variant("Archipelago Classic JS", js),
               {"name": "Driftwood", "appearance": "dark",
                "style": {**ember_style, "syntax": ember_syntax}}],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(theme, indent=2) + "\n")
print(f"wrote {OUT}")
