import itertools
import random
import re

from ..wildcard_loader import (
    process,
    get_wildcard_value,
    wildcard_normalize,
)


class InsaneWildcards:
    """
    Hybrid wildcard processor node that combines features of wildcard
    processing, dynamic prompt generation, and multi-line batch output.

    - Reads wildcards from the 'wildcards/' directory (__keyword__ syntax)
    - Supports {option1|option2} expressions with probability weighting
    - Multiple generation modes: random, combinatorial
    - Batch processing of multi-line input with row limits
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wildcard_text": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "tooltip": "Enter text with wildcard syntax (__keyword__). "
                                   "Each line can be processed independently.",
                    },
                ),
                "populated_text": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                        "tooltip": "Shows the processed result. In 'fixed' mode the "
                                   "value here is used as-is. In 'populate' mode it is "
                                   "overwritten with the processed wildcard_text.",
                    },
                ),
                "mode": (
                    ["populate", "fixed", "reproduce"],
                    {
                        "default": "populate",
                        "tooltip": (
                            "populate: Processes wildcard_text and outputs the result.\n"
                            "fixed: Skips processing, outputs populated_text as-is.\n"
                            "reproduce: Runs as 'fixed' once, then switches to 'populate'."
                        ),
                    },
                ),
                "gen_type": (
                    ["random", "combinatorial"],
                    {
                        "default": "random",
                        "tooltip": "random: Picks random wildcard options for each line.\n"
                                   "combinatorial: Generates all possible combinations from wildcards.",
                    },
                ),
                "seed_type": (
                    ["fixed", "sequential", "random"],
                    {
                        "default": "random",
                        "tooltip": (
                            "fixed: Same seed for all generations.\n"
                            "sequential: Seeds increment from the base seed.\n"
                            "random: Random seeds seeded by the base seed."
                        ),
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Base seed for wildcard processing.",
                    },
                ),
                "max_rows": (
                    "INT",
                    {
                        "default": 1000,
                        "min": 1,
                        "max": 9999,
                        "tooltip": "Maximum number of lines to process from input.",
                    },
                ),
                "remove_empty_lines": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "enabled",
                        "label_off": "disabled",
                        "tooltip": "Remove empty lines from input before processing.",
                    },
                ),
                "Select to add Wildcard": (
                    ["Select the Wildcard to add to the text"],
                ),
            },
        }

    CATEGORY = "InsaneWildcards"

    DESCRIPTION = (
        "A powerful hybrid wildcard processor that generates text prompts "
        "using wildcard syntax. Supports random and combinatorial generation, "
        "multi-line batch input, seed management, and probability-weighted options.\n\n"
        "Syntax:\n"
        "  __keyword__       - Replaced with a random option from the matching wildcard file\n"
        "  {opt1|opt2}       - Random selection from inline options\n"
        "  {2$$opt1|opt2}    - Select 2 items\n"
        "  {1-3$$opt1|opt2}  - Select 1 to 3 items\n"
        "  0.5::option       - Weighted probability\n"
        "  # Comment line     - Line is ignored and merged with next line\n"
        "  #N#__keyword__     - Repeat wildcard N times"
    )

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("text", "seed", "count", "STRING")
    OUTPUT_IS_LIST = (True, True, False, True)
    FUNCTION = "process_node"

    @staticmethod
    def _parse_brace_options(inner):
        """Parse the inner content of a {a|b|c} group and return clean options.
        Handles probability (0.5::a) and multi-select (N$$, N-M$$sep$$) syntax.
        """
        raw_options = inner.split("|")
        # Check if first option is a multi-select header (N$$ or N-M$$sep$$)
        first_parts = raw_options[0].split("$$")
        if len(first_parts) > 1 and re.match(r"^(\d+(-\d+)?)$", first_parts[0]):
            # N$$a|b|c → a, b, c (multi-select count ignored in combinatorial)
            # N-M$$sep$$a|b|c → a, b, c (range and separator ignored)
            raw_options[0] = first_parts[-1]
        # Strip probability prefix from each option: 0.5::a → a
        cleaned = []
        for opt in raw_options:
            clean = re.sub(r"^\s*[0-9.]+::", "", opt, count=1)
            cleaned.append(clean)
        return cleaned

    def _split_lines(self, text, remove_empty_lines, max_rows):
        """Split text into lines, optionally filtering empties, capped by max_rows."""
        lines = text.split("\n")
        if remove_empty_lines:
            lines = [ln for ln in lines if ln.strip()]
        return lines[:max_rows]

    def _generate_seeds(self, seed_type, base_seed, count):
        """Generate a list of seeds."""
        if count <= 0:
            return []
        if seed_type == "fixed":
            return [base_seed] * count
        elif seed_type == "sequential":
            return [base_seed + i for i in range(count)]
        else:  # random
            random.seed(base_seed)
            return [random.randint(0, 0xFFFFFFFFFFFFFFFF) for _ in range(count)]

    def process_node(
        self,
        wildcard_text,
        populated_text,
        mode,
        gen_type,
        seed_type,
        seed,
        max_rows,
        remove_empty_lines,
        **kwargs,
    ):
        # ---- resolve mode ----
        if mode == "reproduce":
            if not hasattr(self, '_reproduce_once') or not self._reproduce_once:
                # First run → treat as fixed, mark for next populate
                self._reproduce_once = True
                mode = "fixed"
            else:
                # Subsequent runs → populate and reset flag
                self._reproduce_once = False
                mode = "populate"

        # ---- fixed mode: return populated_text as-is after line splitting ----
        if mode == "fixed":
            lines = self._split_lines(populated_text, remove_empty_lines, max_rows)
            if not lines:
                return ([""], [0], 0, [""])
            seeds = self._generate_seeds(seed_type, seed, len(lines))
            return (lines, seeds, len(lines), lines)

        # ---- populate mode: process wildcard_text ----
        lines = self._split_lines(wildcard_text, remove_empty_lines, max_rows)
        if not lines:
            return ([""], [0], 0, [""])

        results = []
        result_seeds = []

        if gen_type == "combinatorial":
            # Generate all possible combinations for each line
            for i, line in enumerate(lines):
                opt_pat = r"(?<!\\)\{((?:[^{}]|(?<=\\)[{}])*?)(?<!\\)\}"
                opt_matches = list(re.finditer(opt_pat, line))

                # Collect all dimensions for itertools.product
                all_dims = []
                dim_keys = []  # ('option', full_match) or ('wildcard', key)

                # ---- Add ALL {a|b|c} groups as dimensions (including __ inside) ----
                for m in opt_matches:
                    full = m.group(0)
                    inner = m.group(1)
                    options = self._parse_brace_options(inner)
                    if options:
                        all_dims.append(options)
                        dim_keys.append(('option', full))

                # ---- Add standalone __keyword__ outside of {a|b|c} groups as dimensions ----
                # Remove all {a|b|c} groups from the line to find only standalone wildcards
                line_no_braces = re.sub(opt_pat, "", line)
                wc_pat = r"__([\w.\-+/*\\]+?)__"
                standalone_keys = list(dict.fromkeys(re.findall(wc_pat, line_no_braces)))
                for kw in standalone_keys:
                    vals = get_wildcard_value(wildcard_normalize(kw.lower()))
                    if vals is not None:
                        all_dims.append(vals)
                    else:
                        all_dims.append([f"__{kw}__"])
                    dim_keys.append(('wildcard', f"__{kw}__"))

                if all_dims:
                    base_seed_val = seed if seed_type == "fixed" else seed + i
                    for combo_idx, combo in enumerate(
                        itertools.product(*all_dims)
                    ):
                        resolved = line
                        for (dim_type, key), val in zip(dim_keys, combo):
                            resolved = resolved.replace(key, str(val), 1)
                        # Resolve nested wildcards inside brace options via process()
                        resolved = process(resolved, base_seed_val + combo_idx)
                        results.append(resolved)
                        result_seeds.append(base_seed_val + combo_idx)
                else:
                    # No wildcards or options → normal random processing
                    processed = process(line, seed)
                    results.append(processed)
                    result_seeds.append(seed if seed_type == "fixed" else seed + i)
        else:
            # Random: process each line independently
            seeds = self._generate_seeds(seed_type, seed, len(lines))
            for i, line in enumerate(lines):
                processed = process(line, seeds[i])
                results.append(processed)
                result_seeds.append(seeds[i])

        return (results, result_seeds, len(results), results)
