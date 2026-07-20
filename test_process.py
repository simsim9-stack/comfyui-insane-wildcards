"""Test for combinatorial mode with nested wildcards"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from insane_wildcards.nodes.insane_wildcards_node import InsaneWildcards
from insane_wildcards.wildcard_loader import wildcard_dict

# Setup mock wildcards
wildcard_dict["bo/random/anything"] = [
    "{ __bo/audio/random__| __bo/books/random__| __bo/chars/random__ }"
]
wildcard_dict["bo/audio/random"] = ["audio_value"]
wildcard_dict["bo/books/random"] = ["books_value"]
wildcard_dict["bo/chars/random"] = ["chars_value"]

# Wildcard that contains {a|b} that should also be resolved
wildcard_dict["test/colors"] = ["red", "green", "blue"]
wildcard_dict["test/animals"] = ["cat", "dog"]

node = InsaneWildcards()

print("=== TEST 1: random mode (should resolve everything) ===")
random.seed(42)
r_text, r_seed, r_count, r_string = node.process_node(
    wildcard_text="__bo/random/anything__\nanimal: __test/animals__",
    populated_text="",
    mode="populate",
    gen_type="random",
    seed_type="fixed",
    seed=42,
    max_rows=100,
    remove_empty_lines=True,
)
for i, (t, s) in enumerate(zip(r_text, r_seed)):
    print(f"  Line {i}: {repr(t)} (seed={s})")
print(f"  count={r_count}, STRING={repr(r_string)}")
print()

print("=== TEST 2: combinatorial mode (should resolve everything) ===")
r_text, r_seed, r_count, r_string = node.process_node(
    wildcard_text="__bo/random/anything__\nanimal: __test/animals__",
    populated_text="",
    mode="populate",
    gen_type="combinatorial",
    seed_type="fixed",
    seed=42,
    max_rows=100,
    remove_empty_lines=True,
)
print(f"  Total results: {r_count}")
for i, (t, s) in enumerate(zip(r_text, r_seed)):
    if "... " in t or len(t) > 60:
        t_short = t[:60] + "..."
    else:
        t_short = t
    print(f"  {i}: {repr(t_short)} (seed={s})")
print(f"  STRING={repr(r_string)}")
print()

print("=== TEST 3: combinatorial mode with {a|b} directly in text ===")
r_text, r_seed, r_count, r_string = node.process_node(
    wildcard_text="hello {big|small|huge} world",
    populated_text="",
    mode="populate",
    gen_type="combinatorial",
    seed_type="fixed",
    seed=42,
    max_rows=100,
    remove_empty_lines=True,
)
print(f"  Total: {r_count}")
for i, (t, s) in enumerate(zip(r_text, r_seed)):
    print(f"  {i}: {repr(t)}")
print()

print("=== VERIFICATION ===")
# Check that NO {a|b} or __keyword__ remain in outputs
all_ok = True
r_combined = r_text  # use latest test
for t in r_text:
    if "{" in t and "}" in t:
        print(f"  WARNING: {repr(t)} still contains braces!")
        all_ok = False
    if "__" in t and re.search(r"__\w+", t):
        print(f"  WARNING: {repr(t)} still contains wildcards!")
        all_ok = False

if all_ok:
    print("  All results properly resolved OK")
else:
    print("  Some results not fully resolved FAIL")

print()
print("DONE")
