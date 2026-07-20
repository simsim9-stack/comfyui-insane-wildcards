# Insane Wildcards

A powerful ComfyUI custom node for wildcard processing, dynamic prompt generation, and multi-line batch output — all in one versatile tool.

Node name in ComfyUI: **Insane Wildcards**
Node ID: `InsaneWildcards`
Category: `InsaneWildcards`

---

## Features

- **Wildcard processing** — `__keyword__` syntax reads from `wildcards/` folder (TXT & YAML)
- **Inline options** — `{a|b|c}` random selection with probability weighting `0.5::a`
- **Multi-select** — `{2$$a|b|c}` pick N items, `{1-3$$a|b|c}` pick range
- **Generation modes** — `random` (per-line) or `combinatorial` (all combinations via `itertools.product`)
- **Combinatorial `{a|b}`** — inline options work alongside `__keyword__` in combinatorial mode
- **Seed management** — `fixed`, `sequential`, or `random` seed types
- **Multi-line batch** — process multiple prompt lines at once with `max_rows` and `remove_empty_lines`
- **4 outputs** — `text` (list), `seed` (list), `count`, `STRING` (list — PromptLine-compatible)
- **3 modes** — `populate`, `fixed`, `reproduce`
- **Lazy loading** — on-demand wildcard loading for large collections (>50MB)
- **Wildcard selector** — dropdown to browse and insert wildcards into the text field

---

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `text` | STRING (list) | All processed prompt lines, one per item |
| `seed` | INT (list) | Seeds used for each generated line |
| `count` | INT | Number of generated results |
| `STRING` | STRING (list) | Same as `text`, compatible with PromptLine-expecting nodes |

---

## Syntax

```
__keyword__       — Replaced with a random option from the matching wildcard file
{opt1|opt2}       — Random selection from inline options
{2$$opt1|opt2}    — Select 2 items from the list
{1-3$$opt1|opt2}  — Select 1 to 3 items
0.5::option       — Weighted probability (in wildcard files or inline)
# Comment line    — Line is merged with the next line
#N#__keyword__    — Repeat wildcard selection N times
*/name            — Depth-agnostic wildcard matching
```

---

## Installation

1. Copy `insane_wildcards/` to `ComfyUI/custom_nodes/`
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Restart ComfyUI

---

## File Structure

```
insane_wildcards/
├── __init__.py               # Node registration, API endpoint, WEB_DIRECTORY
├── wildcard_loader.py        # Core wildcard engine (parsing, loading, processing)
├── requirements.txt          # PyYAML, numpy
├── README.md                 # This file
├── js/
│   └── insane_wildcards.js   # Frontend: wildcard selector dropdown
├── wildcards/
│   └── example.txt           # Example wildcard file
└── nodes/
    └── insane_wildcards_node.py  # ComfyUI node class
```

---

## Changelog

### Fixed Bugs

- **Fixed mode crash** — `list index out of range` when `populated_text` received an empty list `[]` from another node's STRING output. Fixed by returning `[""]` instead of `[]` as placeholder for empty results, preventing ComfyUI's `slice_dict` from crashing on `[][-1]`.

- **STRING output** — Now behaves like PromptLine: outputs as a list (`OUTPUT_IS_LIST = True`), compatible with downstream nodes that expect list inputs. Previously had incorrect behavior when chaining nodes.

- **Combinatorial `{a|b}` support** — Inline option groups like `{red|blue|green}` now work in combinatorial mode alongside `__keyword__` wildcards. Handles probability syntax (`0.5::a`) and multi-select prefixes (`N$$`).

- **YAML ReaderError crash** — Fixed `yaml.reader.ReaderError: unacceptable character` when YAML files contain unicode control characters. Now catches `yaml.reader.ReaderError` in all 3 YAML loading paths and falls back to UTF-8 with `errors="ignore"`.

- **Wildcard selector UI** — Added JavaScript frontend for the "Select to add Wildcard" dropdown (matching original ImpactWildcardProcessor behavior). The dropdown shows dynamic status, appends `__keyword__` to the text field on selection, and resets to its label.

---

## Author

**InsanE_GeN** — [CivitAI Profile](https://civitai.com/user/InsanE_GeN)
