# Insane Wildcards — Progress Report

**Date**: July 20, 2026
**Test results**: 66/66 PASSED ✅

---

## 📁 Project Structure

```
insane_wildcards/
├── __init__.py          # ComfyUI integration + WEB_DIRECTORY + API endpoint
├── wildcard_loader.py   # Core wildcard processing (process(), load, etc.)
├── nodes/
│   └── insane_wildcards_node.py  # Node definition (INPUT_TYPES, process_node)
├── js/
│   └── insane_wildcards.js       # Frontend: "Select to add Wildcard" dropdown
├── wildcards/           # Default wildcard folder
├── README.md
├── PROGRESS.md          # ← this file
├── test_process.py      # Basic tests
└── test_all_modes.py    # Comprehensive tests (66 tests)
```

---

## ✅ Что работает

### Node inputs
| Input | Type | Status |
|-------|------|--------|
| `wildcard_text` | STRING (multiline) | ✅ |
| `populated_text` | STRING (multiline) | ✅ |
| `mode` | [populate, fixed, reproduce] | ✅ |
| `gen_type` | [random, combinatorial] | ✅ |
| `seed_type` | [fixed, sequential, random] | ✅ |
| `seed` | INT | ✅ |
| `max_rows` | INT (1-9999) | ✅ |
| `remove_empty_lines` | BOOLEAN | ✅ |
| `Select to add Wildcard` | COMBO (dynamic via JS) | ✅ |

### Node outputs
| Output | Type | OUTPUT_IS_LIST | Status |
|--------|------|----------------|--------|
| `text` | STRING | True | ✅ Returns list of processed lines |
| `seed` | INT | True | ✅ Seeds per line (list) |
| `count` | INT | False | ✅ Total count (scalar) |
| `STRING` | STRING | True | ✅ Same as `text` (list, for PromptLine compatibility) |

### Modes
- **populate**: Processes `wildcard_text`, outputs result ✅
- **fixed**: Returns `populated_text` as-is ✅
- **reproduce**: First run = fixed, subsequent = populate ✅

### gen_type
- **random**: Each line processed independently with `process()` (recursive) ✅
- **combinatorial**: All combinations of first-level wildcards, then `process()` for nested ✅

### seed_type
- **fixed**: Same seed for all lines ✅
- **sequential**: Seeds increment from base ✅
- **random**: Random seeds seeded by base seed ✅

### Syntax support
| Syntax | Description | Status |
|--------|-------------|--------|
| `__keyword__` | Random option from wildcard file | ✅ |
| `{a\|b\|c}` | Random inline selection | ✅ |
| `{2$$a\|b\|c}` | Multi-select (pick 2) | ✅ |
| `{1-3$$a\|b\|c}` | Multi-select (pick 1-3) | ✅ |
| `{1-3$$sep$$a\|b\|c}` | Multi-select with custom separator | ✅ |
| `0.5::option` | Probability weighting | ✅ |
| `# Comment` | Comment line (merged with next) | ✅ |
| `#N#__keyword__` | Repeat wildcard N times | ✅ |
| `__*/keyword__` | Glob pattern matching | ✅ |
| Nested `__keyword__` inside wildcard value | ✅ |
| Nested `{a\|b}` inside wildcard value | ✅ |
| Deep nesting (wildcard→wildcard→{a\|b}→wildcard) | ✅ |

---

## 🐛 Починенные баги

### Bug 1: Fixed mode crash (Fixed)
- **Симптом**: ComfyUI crash: `list index out of range in slice_dict`
- **Причина**: Empty list `[]` возвращался в OUTPUT_IS_LIST=True
- **Фикс**: Возвращать `[""]` и `[0]` вместо `[]`

### Bug 2: STRING output (not a bug, expected behavior)
- STRING output возвращает список строк (как PromptLine), не одну строку

### Bug 3: Combinatorial mode не раскрывал вложенные wildcards
- **Симптом**: `__bo/random/anything__` выводил `{ __bo/audio/random__|... }` без раскрытия
- **Причина**: Комбинаторный режим заменял только первый уровень, не вызывал `process()` после
- **Фикс**: Добавлен `resolved = process(resolved, seed)` после комбинаторной замены

### Bug 4: YAML reader error (Fixed)
- **Симптом**: `yaml.reader.ReaderError: unacceptable character #x0080`
- **Причина**: `except` не ловил `yaml.reader.ReaderError`
- **Фикс**: Добавлен в except во всех 3 местах загрузки YAML

### Bug 5: Numpy array conversion (Fixed)
- **Симптом**: `TypeError: only 0-dimensional arrays can be converted to Python scalars`
- **Причина**: `int(rng.integers(size=1))` — массив из 1 элемента не конвертируется
- **Фикс**: `.item()` — `int(rng.integers(size=1).item())`

---

## 📋 JS Frontend

- `insane_wildcards/js/insane_wildcards.js`
- Загружает список wildcards через API `/insanewildcards/wildcards/list`
- Dropdown "Select to add Wildcard" с динамическими опциями
- Callback добавляет выбранный `__keyword__` в `wildcard_text`
- Статусная метка (🟢 Full Cache / 🔵 On-Demand)

---

## 🧪 Test coverage (66 tests)

```
✓ BASIC wildcard replacement          (9 tests)
✓ {a|b} inline options                (6 tests)
✓ Modes: populate/fixed/reproduce     (6 tests)
✓ gen_type: random/combinatorial      (10 tests)
✓ seed_type: fixed/sequential/random  (5 tests)
✓ max_rows / remove_empty_lines       (5 tests)
✓ process() function directly         (14 tests)
✓ Glob patterns                       (1 test)
✓ Output structure                    (9 tests)
✓ Multi-line + combinatorial          (1 test)
```

---
тест {__bo/random/anything__|__bo/chars/char-magical/male/boconstructions__|__bo/chars/class-profession-regular__}, {__bo/random/anything__|__bo/chars/char-magical/male/boconstructions__|__bo/chars/class-profession-regular__}-------------------
mode fixed gen_type random - пустой вывод
mode reproduse gen_type random - то пустой вывод то выводит строку
mode populate gen_type random - работает 1 строка как надо
mode populate gen_type combo - работает
mode fixed gen_type combo - пусто
mode reproduse gen_type combo - через раз



---

## 🔗 Source projects
это мы нигде не указываем нахер оно нужно, у нас своя нода
- **ImpactWildcardProcessor** from [comfyui-impact-pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)
- **Dynamic Prompt** from [comfyui-et_dynamicprompts](https://github.com/EvaisaDev/ComfyUI-Et-Dynamicprompts)
- **PromptLine** from [comfyui-easy-use](https://github.com/yolain/ComfyUI-Easy-Use)

публикуй на гитхаб.
также укажи в ридми https://civitai.com/user/InsanE_GeN мой аккаунт на civitai



