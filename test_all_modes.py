"""
COMPREHENSIVE TEST: InsaneWildcards All Modes
Tests every combination of: mode, gen_type, seed_type, syntax features
"""
import os, sys, re, random, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from insane_wildcards.nodes.insane_wildcards_node import InsaneWildcards
from insane_wildcards.wildcard_loader import process, wildcard_dict, get_wildcard_value, wildcard_normalize

# ===========================================================================
# SETUP: Seed wildcards for testing
# ===========================================================================
wildcard_dict.clear()
wildcard_dict["test/lorem"] = [
    "lorem ipsum dolor sit amet",
    "consectetur adipiscing elit",
    "sed do eiusmod tempor",
]
wildcard_dict["test/colors"] = ["red", "green", "blue", "yellow"]
wildcard_dict["test/animals"] = ["cat", "dog", "bird", "fish"]

# Nested wildcard: value contains {a|b} with sub-wildcards
wildcard_dict["test/nested_brace"] = [
    "{ __test/colors__| __test/animals__ }"
]

# Wildcard with sub-wildcards (no braces)
wildcard_dict["test/nested_direct"] = [
    "color: __test/colors__",
    "animal: __test/animals__",
]

# Multi-level nesting
wildcard_dict["test/deep"] = [
    "__test/nested_direct__ plus __test/lorem__"
]

# Probability
wildcard_dict["test/prob"] = [
    "0.1::rare",
    "0.9::common",
]

# Multi-select in file
wildcard_dict["test/multi"] = ["a", "b", "c", "d", "e"]

node = InsaneWildcards()

passed = 0
failed = 0
errors = []

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name} {detail}"
        print(msg)
        errors.append(msg)

def run_test(name, **kwargs):
    """Run process_node with given kwargs and return results."""
    defaults = dict(
        wildcard_text="",
        populated_text="",
        mode="populate",
        gen_type="random",
        seed_type="fixed",
        seed=42,
        max_rows=100,
        remove_empty_lines=True,
    )
    defaults.update(kwargs)
    try:
        return node.process_node(**defaults)
    except Exception as e:
        errors.append(f"  [ERROR] {name}: {e}")
        print(f"  [ERROR] {name}: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None

print("=" * 70)
print("INSANE WILDCARDS - COMPREHENSIVE MODE TEST")
print("=" * 70)

# ===========================================================================
# 1. BASIC: Simple wildcard replacement
# ===========================================================================
print("\n--- 1. BASIC wildcard replacement ---")

t, s, c, st = run_test("1a", wildcard_text="__test/lorem__")
check("1a text output", t and isinstance(t, list) and len(t) > 0)
check("1a seed output", s and isinstance(s, list))
check("1a count", c == len(t))
check("1a STRING output", st and isinstance(st, list) and len(st) > 0)
check("1a no raw wildcards", t and not any("__test/" in x for x in t))
check("1a valid content", t and all(len(x.strip()) > 0 for x in t))

# 1b. Multi-line
t, s, c, st = run_test("1b", wildcard_text="__test/colors__\n__test/animals__")
check("1b multi-line count", c == 2)
check("1b multi-line text", t and len(t) == 2)
check("1b no raw wildcards", t and not any("__test/" in x for x in t))

# ===========================================================================
# 2. {a|b} INLINE OPTIONS
# ===========================================================================
print("\n--- 2. {a|b} inline options ---")

t, s, c, st = run_test("2a", wildcard_text="hello {world|earth|planet}")
check("2a resolved", t and not any("{" in x for x in t))
check("2a one result", c == 1)
check("2a valid word", t and t[0] in ["hello world", "hello earth", "hello planet"])

t, s, c, st = run_test("2b", wildcard_text="{3$$a|b|c|d|e}")
check("2b resolved", t and not any("{" in x for x in t))

results_probs = []
for seed_val in range(100):
    t, _, _, _ = run_test("2c_seed"+str(seed_val), wildcard_text="result: {0.1::rare|0.9::common}", seed=seed_val)
    if t:
        results_probs.append(t[0])
has_rare = any("rare" in x for x in results_probs)
has_common = any("common" in x for x in results_probs)
check("2c probability rare found", has_rare)
check("2c probability common found", has_common)

# ===========================================================================
# 3. MODES: populate / fixed / reproduce
# ===========================================================================
print("\n--- 3. Modes: populate / fixed / reproduce ---")

t, s, c, st = run_test("3a", mode="populate", wildcard_text="__test/colors__")
check("3a populate works", t and not any("__test/" in x for x in t))

t, s, c, st = run_test("3b", mode="fixed", populated_text="hello\nworld")
check("3b fixed count", c == 2)
check("3b fixed unchanged", t == ["hello", "world"])

node._reproduce_once = False
t1, s1, c1, st1 = run_test("3c_r1", mode="reproduce", populated_text="fixed output", wildcard_text="__test/colors__")
check("3c reproduce first=fixed", t1 == ["fixed output"])
t2, s2, c2, st2 = run_test("3c_r2", mode="reproduce", populated_text="fixed output", wildcard_text="__test/colors__")
check("3c reproduce second=populate", t2 and not any("__test/" in x for x in t2))
check("3c reproduce second has color", t2 and len(t2) > 0 and len(t2[0]) > 0)

# ===========================================================================
# 4. gen_type: random / combinatorial
# ===========================================================================
print("\n--- 4. gen_type: random / combinatorial ---")

# 4a. random mode
t, s, c, st = run_test("4a", gen_type="random", wildcard_text="__test/colors__")
check("4a random", t and len(t) == 1)

# 4b. combinatorial basic
t, s, c, st = run_test("4b", gen_type="combinatorial", wildcard_text="__test/colors__")
check("4b combinatorial count", c == 4)
check("4b all colors present", t and set(t) == {"red", "green", "blue", "yellow"})

# 4c. combinatorial with {a|b}
t, s, c, st = run_test("4c", gen_type="combinatorial", wildcard_text="hello {world|earth|planet} {big|small}")
check("4c combination count", c == 6)
variations = []
for a in ["world", "earth", "planet"]:
    for b in ["big", "small"]:
        variations.append(f"hello {a} {b}")
check("4c correct combos", set(t) == set(variations))

# 4d. combinatorial + __keyword__ + {a|b} mixed
t, s, c, st = run_test("4d", gen_type="combinatorial", wildcard_text="__test/colors__ {big|small}")
check("4d mixed count", c == 8)

# 4e. combinatorial with nested wildcards
t, s, c, st = run_test("4e", gen_type="combinatorial", wildcard_text="__test/nested_brace__")
check("4e nested in combinatorial", t and len(t) > 0)
check("4e no braces remain", not any("{" in x for x in t) if t else True)
check("4e no wildcards remain", not any("__test/" in x for x in t) if t else True)

# ===========================================================================
# 5. THE FIX: {__x__|__y__} groups in combinatorial
# ===========================================================================
print("\n--- 5. {__x__|__y__} groups in combinatorial (THE BUG FIX) ---")

# 5a. Two identical {opt|opt} groups
# 2 options x 2 groups = 4
t, s, c, st = run_test("5a", gen_type="combinatorial",
    wildcard_text="{hello|world}, {foo|bar}, 123",
    seed=42)
check("5a two brace groups count", c == 4)  # 2 x 2 from two {..}
# Since these don't contain __keyword__ inside, they work as plain {a|b} groups

# 5b. Three {__kw__|__kw__|__kw__} groups
# Each group has 3 raw __keyword__ options
# Should be: 3 x 3 x 3 = 27
# But these contain __ inside, so they were SKIPPED before the fix
# We need wildcards that exist for this test
wildcard_dict["test/opt_a"] = ["a_val"]
wildcard_dict["test/opt_b"] = ["b_val"]
wildcard_dict["test/opt_c"] = ["c_val"]

t, s, c, st = run_test("5b", gen_type="combinatorial",
    wildcard_text="{__test/opt_a__|__test/opt_b__|__test/opt_c__}, {__test/opt_a__|__test/opt_b__|__test/opt_c__}, {x|y|z}123",
    seed=42)
check("5b three brace groups with __ inside", c == 27)  # 3 x 3 x 3
check("5b no raw braces remain", not any("{" in x for x in t) if t else True)
check("5b all resolved", t and all("__test/" not in x for x in t))
# Verify we have the right number of unique results
check("5b unique results", len(set(t)) == len(t))

# 5c. {__kw__|...} groups + standalone __keyword__
t, s, c, st = run_test("5c", gen_type="combinatorial",
    wildcard_text="{__test/opt_a__|__test/opt_b__} __test/colors__",
    seed=42)
# 2 brace options x 4 colors = 8
check("5c mixed brace+wildcard", c == 8)
check("5c no raw braces", not any("{" in x for x in t) if t else True)
check("5c no raw wildcards", not any("__test/" in x for x in t) if t else True)

# 5d. The EXACT user scenario: {__kw__|__kw__|__kw__}, {__kw__|__kw__|__kw__}, {a|b|c}123
# With brace-plus-__ fix: 3 x 3 x 3 = 27
# Without fix: only 3 (from the last {a|b|c})
t, s, c, st = run_test("5d", gen_type="combinatorial",
    wildcard_text="{__test/opt_a__|__test/opt_b__|__test/opt_c__}, {__test/opt_a__|__test/opt_b__|__test/opt_c__}, {a|b|c}123",
    seed=42)
check("5d user scenario: 3x3x3=27", c == 27)

# 5e. Brace-with-__ duplicate positions - was: replace only 1st occurrence
t, s, c, st = run_test("5e", gen_type="combinatorial",
    wildcard_text="{__test/opt_a__|__test/opt_b__}, {__test/opt_a__|__test/opt_b__}",
    seed=42)
check("5e two identical brace groups", c == 4)

# ===========================================================================
# 6. seed_type: fixed / sequential / random
# ===========================================================================
print("\n--- 6. seed_type: fixed / sequential / random ---")

t1, _, _, _ = run_test("6a_1", seed_type="fixed", seed=42, wildcard_text="__test/lorem__")
t2, _, _, _ = run_test("6a_2", seed_type="fixed", seed=42, wildcard_text="__test/lorem__")
check("6a fixed seed deterministic", t1 == t2)

t3, _, _, _ = run_test("6a_3", seed_type="fixed", seed=99, wildcard_text="__test/lorem__")
check("6b different seed different result", len(set([t1[0], t3[0]])) > 1 if t1 and t3 else True)

t, s, _, _ = run_test("6c", seed_type="sequential", seed=100, wildcard_text="__test/lorem__\n__test/lorem__")
check("6c sequential seeds", s == [100, 101])

t, s, _, _ = run_test("6d", seed_type="random", seed=42, wildcard_text="__test/lorem__\n__test/lorem__")
check("6d random seeds", s and len(s) == 2)
check("6d random seeds different from base", all(x != 42 for x in s))

# ===========================================================================
# 7. max_rows / remove_empty_lines
# ===========================================================================
print("\n--- 7. max_rows / remove_empty_lines ---")

input_10 = "\n".join([f"line {i}" for i in range(10)])
t, s, c, st = run_test("7a", mode="fixed", populated_text=input_10, max_rows=3)
check("7a max_rows 3", c == 3)
check("7a max_rows limited", len(t) == 3)

input_with_empty = "hello\n\nworld\n\n\nfoo"
t, s, c, st = run_test("7b", mode="fixed", populated_text=input_with_empty, remove_empty_lines=True)
check("7b remove_empty", c == 3)
check("7b no empty lines", all(len(x.strip()) > 0 for x in t))

t, s, c, st = run_test("7c", mode="fixed", populated_text=input_with_empty, remove_empty_lines=False)
check("7c keep empty", c == 6)

# ===========================================================================
# 8. PROCESS() function directly
# ===========================================================================
print("\n--- 8. process() function directly ---")

for seed_val in [1, 2, 3]:
    r = process("__test/lorem__", seed=seed_val)
    check(f"8a process seed={seed_val}", r and len(r) > 0 and "__test/" not in r)

for seed_val in [10, 20, 30]:
    r = process("__test/nested_brace__", seed=seed_val)
    check(f"8b nested brace seed={seed_val}", r and "{" not in r and "__test/" not in r)

for seed_val in [50, 60]:
    r = process("__test/deep__", seed=seed_val)
    check(f"8c deep nesting seed={seed_val}", r and len(r) > 0 and "__test/" not in r)
    check(f"8c deep resolved", "color:" in r or "animal:" in r)

count_rare = 0
count_common = 0
for seed_val in range(200):
    r = process("__test/prob__", seed=seed_val)
    if "rare" in r:
        count_rare += 1
    elif "common" in r:
        count_common += 1
check("8d prob rare some", count_rare > 0)
check("8d prob common some", count_common > 0)
check("8d prob rare < common", count_rare < count_common)

# ===========================================================================
# 9. GLOB patterns
# ===========================================================================
print("\n--- 9. Glob patterns ---")

wildcard_dict["test/glob/fruit/apple"] = ["red apple"]
wildcard_dict["test/glob/fruit/banana"] = ["yellow banana"]
wildcard_dict["test/glob/color/red"] = ["bright red"]
wildcard_dict["test/glob/color/blue"] = ["ocean blue"]

t, s, c, st = run_test("9", gen_type="random", wildcard_text="__test/glob/fruit/*__")
check("9 glob found something", t and len(t) > 0)

# ===========================================================================
# 10. OUTPUT STRUCTURE
# ===========================================================================
print("\n--- 10. Output structure ---")

t, s, c, st = run_test("10a", wildcard_text="__test/lorem__")
check("10a text is list", isinstance(t, list))
check("10a seed is list", isinstance(s, list))
check("10a count is int", isinstance(c, int))
check("10a STRING is list", isinstance(st, list))
check("10a text == STRING", t == st)
check("10a seed len == count", len(s) == c)
check("10a seed[0] is int", isinstance(s[0], int))

t, s, c, st = run_test("10b", wildcard_text="")
check("10b empty text placeholder", t == [""] if t else True)
check("10b empty count zero", c == 0)
check("10b empty STRING placeholder", st == [""] if st else True)

# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "=" * 70)
print(f"SUMMARY: {passed} passed, {failed} failed, {len(errors) - failed} errors")
print("=" * 70)

if failed > 0 or len(errors) > failed:
    print("\nIssues:")
    for e in errors:
        print(e)
else:
    print("\nALL TESTS PASSED!")

print("\nDone.")
