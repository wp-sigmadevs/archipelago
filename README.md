# Archipelago

JetBrains Islands-inspired dark themes and Atom Material file icons for [Zed](https://zed.dev).

| Theme | What |
|---|---|
| **Driftwood** | Refined One Dark: readable teal calls, green italic properties, One Dark-tinted chrome, soft inlay-hint pills |
| **Archipelago Classic** | Islands Dark UI with a PHP-tuned One Dark editor scheme |
| **Archipelago Classic JS** | The same, tuned for JS/TS |
| **Archipelago Icons** | Atom Material Icons: 2,600+ file types, 2,600+ folder names |

## Install

Two extensions (Zed doesn't allow themes and icons in one): Zed → `cmd-shift-x` → install **Archipelago** (themes) and **Archipelago Icons**. Then pick the theme (`cmd-k cmd-t`) and icon theme (`zed: toggle icon theme`).

| Folder | Extension |
|---|---|
| `theme/` | Archipelago (colour themes) |
| `icons/` | Archipelago Icons (icon theme) |

## Recommended settings

```jsonc
"colorize_brackets": true,
"indent_guides": { "coloring": "indent_aware", "background_coloring": "indent_aware" },
"inlay_hints": { "enabled": true, "show_background": true }
```

### WebStorm-style JS/TS colours (optional)

The themes define `ts.*` styles for language-server semantic tokens:

```jsonc
"languages": {
  "TypeScript": { "semantic_tokens": "combined" },
  "TSX": { "semantic_tokens": "combined" },
  "JavaScript": { "semantic_tokens": "combined" }
},
"global_lsp_settings": {
  "semantic_token_rules": [
    { "token_type": "variable", "token_modifiers": ["local"], "style": ["ts.variable.local"] },
    { "token_type": "variable", "style": ["ts.variable"] },
    { "token_type": "parameter", "style": ["ts.parameter"] },
    { "token_type": "property", "style": ["ts.property"], "font_style": "normal" },
    { "token_type": "function", "style": ["ts.function"] },
    { "token_type": "member", "style": ["ts.function"] },
    { "token_type": "class", "style": ["ts.type"] },
    { "token_type": "interface", "style": ["ts.type"] },
    { "token_type": "type", "style": ["ts.type"] },
    { "token_type": "typeParameter", "style": ["ts.type"] },
    { "token_type": "enum", "style": ["ts.type"] },
    { "token_type": "enumMember", "style": ["ts.enum_member"] }
  ]
}
```

Italic keywords and properties need a font with an italic face, e.g. JetBrains Mono.

## Building

The theme and icons are generated from a local JetBrains IDE install:

- `python3 generate.py` — themes from a PhpStorm colour scheme (`.icls`) and the Islands Dark UI theme
- `python3 generate_icons.py` — icon theme from the Atom Material Icons plugin

## License

MIT. Icons and file associations: Atom Material Icons © Elior "Mallowigi" Boukhobza, MIT (see `icons/LICENSE-ICONS`). Not affiliated with JetBrains.
