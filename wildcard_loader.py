import logging
import os
import random
import re
import threading

import numpy as np

try:
    import yaml
except ImportError:
    yaml = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
wildcards_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "wildcards")
)

RE_WildCardQuantifier = re.compile(
    r"(?P<quantifier>\d+)#__(?P<keyword>[\w.\-+/*\\]+?)__", re.IGNORECASE
)
wildcard_lock = threading.Lock()
wildcard_dict = {}

# Cache limit (default 50 MB)
WILDCARD_CACHE_LIMIT = 50 * 1024 * 1024
_on_demand_mode = False

# Two-phase loading
available_wildcards = {}  # key -> file_path
loaded_wildcards = {}     # key -> loaded data


# ---------------------------------------------------------------------------
# Lazy wildcard loader
# ---------------------------------------------------------------------------
class LazyWildcardLoader:
    """Lazy loader that reads file contents only on first access."""

    def __init__(self, file_path, file_type="txt"):
        self.file_path = file_path
        self.file_type = file_type
        self._data = None
        self._loaded = False

    # ------------------------------------------------------------------ data
    def _load_txt(self):
        try:
            with open(self.file_path, "r", encoding="ISO-8859-1") as f:
                lines = f.read().splitlines()
        except (UnicodeDecodeError, OSError):
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
        return [x for x in lines if x.strip() and not x.strip().startswith("#")]

    def _load_yaml(self):
        if yaml is None:
            logging.warning("[InsaneWildcards] PyYAML not installed, skipping YAML file %s", self.file_path)
            return []
        try:
            with open(self.file_path, "r", encoding="ISO-8859-1") as f:
                return yaml.load(f, Loader=yaml.FullLoader)
        except (yaml.reader.ReaderError, UnicodeDecodeError, OSError):
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                return yaml.load(f, Loader=yaml.FullLoader)

    def get_data(self):
        if not self._loaded:
            with wildcard_lock:
                if not self._loaded:
                    if self.file_type == "txt":
                        self._data = self._load_txt()
                    elif self.file_type in ("yaml", "yml"):
                        self._data = self._load_yaml()
                    self._loaded = True
        return self._data

    def __getitem__(self, index):
        return self.get_data()[index]

    def __iter__(self):
        return iter(self.get_data())

    def __len__(self):
        return len(self.get_data())

    def __contains__(self, item):
        return item in self.get_data()

    def __bool__(self):
        return len(self.get_data()) > 0

    def count(self, value):
        return self.get_data().count(value)

    def index(self, value, start=0, stop=None):
        if stop is None:
            return self.get_data().index(value, start)
        return self.get_data().index(value, start, stop)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def calculate_directory_size(directory_path, limit=None):
    total = 0
    try:
        for root, _dirs, files in os.walk(directory_path, followlinks=True):
            for fname in files:
                if fname.endswith((".txt", ".yaml", ".yml")):
                    try:
                        total += os.path.getsize(os.path.join(root, fname))
                        if limit and total >= limit:
                            return total
                    except OSError:
                        pass
    except OSError:
        pass
    return total


def wildcard_normalize(x):
    return x.replace("\\", "/").replace(" ", "-").lower()


def scan_wildcard_metadata(wcard_path):
    """Scan directory for wildcard files – metadata only (no data loading)."""
    global available_wildcards
    discovered = 0
    try:
        for root, _dirs, files in os.walk(wcard_path, followlinks=True):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, wcard_path)
                if fname.endswith(".txt"):
                    key = wildcard_normalize(os.path.splitext(rel)[0])
                    available_wildcards[key] = fpath
                    discovered += 1
                elif fname.endswith((".yaml", ".yml")):
                    key = wildcard_normalize(os.path.splitext(rel)[0])
                    available_wildcards[key] = fpath
                    discovered += 1
    except OSError as e:
        logging.warning("[InsaneWildcards] Error scanning %s: %s", wcard_path, e)
    return discovered


# ---------------------------------------------------------------------------
# File lookup & value retrieval
# ---------------------------------------------------------------------------
def find_wildcard_file(key):
    """Find a wildcard file by key (supports on-demand mode)."""
    extensions = [".txt", ".yaml", ".yml"]
    for ext in extensions:
        fpath = os.path.join(wildcards_path, f"{key}{ext}")
        if os.path.isfile(fpath):
            return fpath, ext in (".yaml", ".yml")

    # Nested YAML key: e.g. "colors/warm" -> parent "colors.yaml"
    if "/" in key:
        parent = key.split("/")[0]
        for ext in (".yaml", ".yml"):
            fpath = os.path.join(wildcards_path, f"{parent}{ext}")
            if os.path.isfile(fpath):
                return fpath, True

    return None, False


def get_wildcard_value(key):
    """Return the list of options for a wildcard key, with on-demand loading."""
    global loaded_wildcards

    if _on_demand_mode:
        if key in loaded_wildcards:
            return loaded_wildcards[key]

        fpath, is_yaml = find_wildcard_file(key)
        if fpath is None:
            # Fallback: depth-agnostic pattern matching
            matched = []
            for k in available_wildcards.keys():
                if (k == key or k.endswith("/" + key)
                        or k.startswith(key + "/")
                        or ("/" + key + "/") in k):
                    matched.append(k)
            all_opts = []
            for mk in matched:
                v = get_wildcard_value(mk)
                if v:
                    all_opts.extend(v)
            if all_opts:
                loaded_wildcards[key] = all_opts
                return all_opts
            return None

        if is_yaml or fpath.endswith((".yaml", ".yml")):
            return None  # YAML pre-loaded at startup

        try:
            data = _load_txt_file(fpath)
            loaded_wildcards[key] = data
            return data
        except Exception as e:
            logging.warning("[InsaneWildcards] Failed to load %s: %s", fpath, e)
            return None

    value = wildcard_dict.get(key)
    if isinstance(value, LazyWildcardLoader):
        return value.get_data()
    return value


def _load_txt_file(fpath):
    with open(fpath, "r", encoding="ISO-8859-1") as f:
        lines = f.read().splitlines()
    return [x for x in lines if x.strip() and not x.strip().startswith("#")]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def read_wildcard(k, v, on_demand=False):
    if isinstance(v, list):
        k = wildcard_normalize(k)
        wildcard_dict[k] = v
    elif isinstance(v, dict):
        for k2, v2 in v.items():
            read_wildcard(f"{k}/{k2}", v2, on_demand)
    elif isinstance(v, str):
        k = wildcard_normalize(k)
        wildcard_dict[k] = [v]
    elif isinstance(v, (int, float)):
        k = wildcard_normalize(k)
        wildcard_dict[k] = [str(v)]


def read_wildcard_dict(wcard_path, on_demand=False):
    global wildcard_dict
    for root, _dirs, files in os.walk(wcard_path, followlinks=True):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, wcard_path)
            if fname.endswith(".txt"):
                key = wildcard_normalize(os.path.splitext(rel)[0])
                if on_demand:
                    wildcard_dict[key] = LazyWildcardLoader(fpath, "txt")
                else:
                    lines = _load_txt_file(fpath)
                    wildcard_dict[key] = lines
            elif fname.endswith((".yaml", ".yml")):
                if yaml is None:
                    continue
                try:
                    with open(fpath, "r", encoding="ISO-8859-1") as f:
                        ydata = yaml.load(f, Loader=yaml.FullLoader)
                except (yaml.reader.ReaderError, UnicodeDecodeError, OSError):
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        ydata = yaml.load(f, Loader=yaml.FullLoader)
                if ydata:
                    for k, v in ydata.items():
                        read_wildcard(k, v, on_demand)
    return wildcard_dict


def load_yaml_files_only(wcard_path):
    """Pre-load YAML files (YAML keys are embedded inside file content)."""
    yaml_count = 0
    if yaml is None:
        return yaml_count
    try:
        for root, _dirs, files in os.walk(wcard_path, followlinks=True):
            for fname in files:
                if fname.endswith((".yaml", ".yml")):
                    fpath = os.path.join(root, fname)
                    try:
                        _load_yaml_wildcard(fpath)
                        yaml_count += 1
                    except Exception as e:
                        logging.warning("[InsaneWildcards] Failed YAML %s: %s", fpath, e)
    except OSError:
        pass
    return yaml_count


def _load_yaml_wildcard(fpath, key_prefix=""):
    global loaded_wildcards
    try:
        with open(fpath, "r", encoding="ISO-8859-1") as f:
            ydata = yaml.load(f, Loader=yaml.FullLoader)
    except (yaml.reader.ReaderError, UnicodeDecodeError, OSError):
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            ydata = yaml.load(f, Loader=yaml.FullLoader)
    if not ydata:
        return []
    result = []
    for k, v in ydata.items():
        if isinstance(v, list):
            sk = wildcard_normalize(f"{key_prefix}/{k}") if key_prefix else wildcard_normalize(k)
            loaded_wildcards[sk] = v
            result.extend(v)
        elif isinstance(v, dict):
            parent_key = wildcard_normalize(k)
            parent_vals = []
            for k2, v2 in v.items():
                sk = wildcard_normalize(f"{k}/{k2}")
                if isinstance(v2, list):
                    loaded_wildcards[sk] = v2
                    parent_vals.extend(v2)
                elif isinstance(v2, str):
                    loaded_wildcards[sk] = [v2]
                    parent_vals.append(v2)
                elif isinstance(v2, (int, float)):
                    loaded_wildcards[sk] = [str(v2)]
                    parent_vals.append(str(v2))
            if parent_vals:
                loaded_wildcards[parent_key] = parent_vals
                result.extend(parent_vals)
        elif isinstance(v, str):
            sk = wildcard_normalize(f"{key_prefix}/{k}") if key_prefix else wildcard_normalize(k)
            loaded_wildcards[sk] = [v]
        elif isinstance(v, (int, float)):
            sk = wildcard_normalize(f"{key_prefix}/{k}") if key_prefix else wildcard_normalize(k)
            loaded_wildcards[sk] = [str(v)]
    return result


def wildcard_load():
    """Load wildcards – switches to on-demand mode when total size exceeds limit."""
    global wildcard_dict, available_wildcards, loaded_wildcards, _on_demand_mode
    wildcard_dict = {}
    available_wildcards = {}
    loaded_wildcards = {}
    _on_demand_mode = False

    cache_limit = WILDCARD_CACHE_LIMIT
    total_size = calculate_directory_size(wildcards_path, limit=cache_limit)

    if total_size >= cache_limit:
        _on_demand_mode = True
        logging.info(
            "[InsaneWildcards] Wildcard size (%.2f MB) exceeds cache (%d MB). "
            "On-demand mode activated.",
            total_size / (1024 * 1024),
            cache_limit // (1024 * 1024),
        )
        txt_count = scan_wildcard_metadata(wildcards_path)
        yaml_count = load_yaml_files_only(wildcards_path)
        logging.info(
            "[InsaneWildcards] On-demand mode: %d TXT (metadata), %d YAML pre-loaded.",
            txt_count,
            yaml_count,
        )
    else:
        logging.info(
            "[InsaneWildcards] Wildcard size (%.2f MB) within cache. Full-load mode.",
            total_size / (1024 * 1024),
        )
        read_wildcard_dict(wildcards_path, on_demand=False)

    logging.info("[InsaneWildcards] Wildcard loading complete.")


def get_wildcard_list():
    """Return list of wildcard keys (as __key__ strings) for UI dropdown."""
    with wildcard_lock:
        if _on_demand_mode:
            return [f"__{x}__" for x in loaded_wildcards.keys()]
        return [f"__{x}__" for x in wildcard_dict.keys()]


def get_wildcard_dict():
    with wildcard_lock:
        return wildcard_dict


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------
def is_numeric_string(s):
    return bool(re.match(r"^-?(\d*\.?\d+|\d+\.?\d*)$", s))


def process_comment_out(text):
    lines = text.split("\n")
    out = []
    flag = False
    for line in lines:
        if line.lstrip().startswith("#"):
            flag = True
            continue
        if not out:
            out.append(line)
        elif flag:
            out[-1] += " " + line
            flag = False
        else:
            out.append(line)
    return "\n".join(out)


def process(text, seed=None):
    """Process wildcard syntax in *text* and return the populated result."""
    text = process_comment_out(text)
    if seed is not None:
        random.seed(seed)
    random_gen = np.random.default_rng(seed)
    local_wildcard_dict = get_wildcard_dict()

    # -------------------------------------------------------------- options
    def replace_options(string):
        replacements_found = False

        def replace_option(match):
            nonlocal replacements_found
            options = match.group(1).split("|")
            multi = options[0].split("$$")
            select_range = None
            select_sep = " "
            range_pat = r"(\d+)(-(\d+))?"
            range_pat2 = r"-(\d+)"
            wildcard_pat = r"__([\w.\-+/*\\]+?)__"

            if len(multi) > 1:
                r = re.match(range_pat, options[0])
                if r is None:
                    r = re.match(range_pat2, options[0])
                    a, b = "1", r.group(1).strip() if r else None
                else:
                    a = r.group(1).strip()
                    b = r.group(3).strip() if r.group(3) else a

                if r is not None and b is not None:
                    if is_numeric_string(a) and is_numeric_string(b):
                        select_range = (int(a), int(b))
                    elif is_numeric_string(a):
                        x = int(a)
                        select_range = (x, x)

                    def expand_wildcard_or_string(opts, pat, wpat):
                        matches = re.findall(wpat, pat)
                        if len(opts) == 1 and matches:
                            return _get_wildcard_options(pat)
                        opts[0] = pat
                        return opts

                    if select_range is not None and len(multi) == 2:
                        options = expand_wildcard_or_string(options, multi[1], wildcard_pat)
                    elif select_range is not None and len(multi) == 3:
                        select_sep = multi[1]
                        options = expand_wildcard_or_string(options, multi[2], wildcard_pat)

            adj_probs = []
            total_prob = 0
            for opt in options:
                parts = opt.split("::", 1) if isinstance(opt, str) else f"{opt}".split("::", 1)
                p = float(parts[0].strip()) if len(parts) == 2 and is_numeric_string(parts[0].strip()) else 1.0
                adj_probs.append(p)
                total_prob += p

            norm_probs = [p / total_prob for p in adj_probs]

            if select_range is None:
                sc = 1
            else:
                def max_val(olen, mr):
                    return min(mr + 1, olen + 1) if mr > 0 else olen + 1

                def sel_count(mv, mn, rng):
                    if max(mv, mn) <= 0:
                        return 0
                    if mv == mn:
                        return mv
                    lo, hi = min(mn, mv), max(mn, mv)
                    return int(rng.integers(low=lo, high=hi, size=1).item())

                sc = sel_count(max_val(len(options), select_range[1]), select_range[0], random_gen)

            if sc > len(options) or total_prob <= 1:
                random_gen.shuffle(options)
                selected = options
            else:
                selected = random_gen.choice(options, p=norm_probs, size=sc, replace=False)

            cleaned = [re.sub(r"^\s*[0-9.]+::", "", str(x), count=1) for x in selected]
            replacements_found = True
            return select_sep.join(cleaned)

        pattern = r"(?<!\\)\{((?:[^{}]|(?<=\\)[{}])*?)(?<!\\)\}"
        result = re.sub(pattern, replace_option, string)
        return result, replacements_found

    # -------------------------------------------------------------- wildcards
    def _get_wildcard_options(string):
        pat = r"__([\w.\-+/*\\]+?)__"
        matches = re.findall(pat, string)
        opts = []
        for m in matches:
            kw = wildcard_normalize(m.lower())
            vals = get_wildcard_value(kw)
            if vals is not None:
                opts.extend(vals)
            elif "*" in kw:
                patterns = []
                sd = available_wildcards if _on_demand_mode else local_wildcard_dict
                if kw.startswith("*/") and len(kw) > 2:
                    base = kw[2:]
                    for k in sd.keys():
                        if (k == base or k.endswith("/" + base)
                                or k.startswith(base + "/")
                                or ("/" + base + "/") in k):
                            v = get_wildcard_value(k)
                            if v:
                                patterns.extend(v)
                else:
                    sub = kw.replace("*", ".*").replace("+", "\\+")
                    for k in sd.keys():
                        if re.match(sub, k) or re.match(sub, k + "/"):
                            v = get_wildcard_value(k)
                            if v:
                                patterns.extend(v)
                opts.extend(patterns)
        return opts

    def replace_wildcard(string):
        pat = r"__([\w.\-+/*\\]+?)__"
        matches = re.findall(pat, string)
        replaced = False
        for m in matches:
            kw = wildcard_normalize(m.lower())
            vals = get_wildcard_value(kw)
            if vals is not None:
                adj_probs = []
                total_prob = 0
                for opt in vals:
                    parts = opt.split("::", 1)
                    p = float(parts[0].strip()) if len(parts) == 2 and is_numeric_string(parts[0].strip()) else 1.0
                    adj_probs.append(p)
                    total_prob += p
                norm_probs = [p / total_prob for p in adj_probs]
                sel = random_gen.choice(vals, p=norm_probs, replace=False)
                repl = re.sub(r"^\s*[0-9.]+::", "", sel, count=1)
                replaced = True
                string = string.replace(f"__{m}__", repl, 1)
            elif "*" in kw:
                patterns = []
                sd = available_wildcards if _on_demand_mode else local_wildcard_dict
                if kw.startswith("*/") and len(kw) > 2:
                    base = kw[2:]
                    for k in sd.keys():
                        if (k == base or k.endswith("/" + base)
                                or k.startswith(base + "/")
                                or ("/" + base + "/") in k):
                            v = get_wildcard_value(k)
                            if v:
                                patterns.extend(v)
                else:
                    sub = kw.replace("*", ".*").replace("+", "\\+")
                    for k in sd.keys():
                        if re.match(sub, k) or re.match(sub, k + "/"):
                            v = get_wildcard_value(k)
                            if v:
                                patterns.extend(v)
                if patterns:
                    repl = str(random_gen.choice(patterns))
                    replaced = True
                    string = string.replace(f"__{m}__", repl, 1)
            elif "/" not in kw:
                string, replaced = replace_wildcard(string.replace(f"__{m}__", f"__*/{m}__", 1))
        return string, replaced

    # -------------------------------------------------------------- main loop
    depth = 100
    stop = False
    while not stop and depth > 1:
        depth -= 1
        # quantifier expansion
        for qm in RE_WildCardQuantifier.finditer(text):
            kw = qm.group("keyword").lower()
            q = int(qm.group("quantifier")) if qm.group("quantifier") else 1
            repl = "__|__".join([kw] * q)
            escaped = kw.replace("*", "\\*")
            text = re.compile(
                rf"(?P<quantifier>\d+)#__(?P<keyword>{escaped})__", re.IGNORECASE
            ).sub(f"__{repl}__", text)

        s1, r1 = replace_options(text)
        while r1:
            s1, r1 = replace_options(s1)

        text, r2 = replace_wildcard(s1)
        stop = not r1 and not r2

    return text
