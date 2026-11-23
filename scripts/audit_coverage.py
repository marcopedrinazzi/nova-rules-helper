#!/usr/bin/env python3
"""Check that every rule has a runnable YAML test referencing its file and name."""
import argparse
import os
import sys
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
from test_rules import load_test_cases, load_rules_from_file
from nova.core.parser import NovaParserError
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation"))
from ci_utils import parse_all_rules


def run_audit(rules_dir: str, tests_dir: str):
    rules_dir = os.path.abspath(rules_dir)
    defined, errors = parse_all_rules(rules_dir)
    for path, error in errors:
        print(f"[FAIL] {path}: {error}")
    if errors or not defined:
        if not defined:
            print("[FAIL] No rules found")
        return 1
    if not os.path.isdir(tests_dir):
        print(f"[FAIL] Tests directory not found: {tests_dir}")
        return 1
    try:
        cases = load_test_cases(tests_dir)
        tested = set()
        cache = {}
        for case in cases:
            path = os.path.abspath(os.path.join(rules_dir, case["_rule_file"]))
            if path not in cache:
                cache[path] = load_rules_from_file(path, rules_dir)
            if case["rule_name"] not in cache[path]:
                raise ValueError(f"{case['_source_yaml']}: unknown rule {case['rule_name']} in {path}")
            if "decision_answers" in case:
                raise ValueError(f"{case['_source_yaml']}: decision_answers is unsupported")
            tested.add((path, case["rule_name"]))
    except (OSError, yaml.YAMLError, NovaParserError, ValueError, TypeError) as error:
        print(f"[FAIL] Invalid test coverage: {error}")
        return 1
    expected = {(os.path.abspath(path), rule.name) for path, rule in defined}
    missing = expected - tested
    covered = len(expected) - len(missing)
    print(f"Rules with runnable cases: {covered}/{len(expected)} ({covered / len(expected):.1%})")
    for path, name in sorted(missing):
        print(f"[FAIL] Missing tests: {os.path.relpath(path, rules_dir)} -> {name}")
    if not missing:
        print("[OK] Every rule has runnable cases; coverage does not establish passing results.")
    return 1 if missing else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules-dir", default=".")
    parser.add_argument("--tests-dir", default="tests")
    args = parser.parse_args()
    sys.exit(run_audit(args.rules_dir, args.tests_dir))
