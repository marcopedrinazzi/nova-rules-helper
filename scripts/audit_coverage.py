#!/usr/bin/env python3
import os
import re
import yaml
import argparse
from typing import Set, Dict, List

def discover_rules(rules_dir: str) -> Dict[str, Set[str]]:
    """Finds all rules defined in .nov files."""
    rules_map = {}
    rule_pattern = re.compile(r"^rule\s+([A-Z][a-zA-Z0-9]*)")
    
    for root, _, files in os.walk(rules_dir):
        for fname in files:
            if fname.endswith(".nov"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r") as f:
                    rules = set()
                    for line in f:
                        match = rule_pattern.match(line.strip())
                        if match:
                            rules.add(match.group(1))
                    rules_map[fpath] = rules
    return rules_map

def discover_tests(tests_dir: str) -> Set[str]:
    """Finds all rule names mentioned in YAML test files."""
    tested_rules = set()
    for root, _, files in os.walk(tests_dir):
        for fname in files:
            if fname.endswith((".yaml", ".yml")):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r") as f:
                        data = yaml.safe_load(f)
                        if data and "tests" in data:
                            for test in data["tests"]:
                                if "rule_name" in test:
                                    tested_rules.add(test["rule_name"])
                except Exception:
                    continue
    return tested_rules

def run_audit(rules_dir: str, tests_dir: str):
    """Reports missing test coverage."""
    rules_map = discover_rules(rules_dir)
    tested_rules = discover_tests(tests_dir)
    
    all_defined_rules = set()
    for rules in rules_map.values():
        all_defined_rules.update(rules)
        
    missing = all_defined_rules - tested_rules
    
    print(f"--- Coverage Audit ---")
    print(f"Total Rules Defined: {len(all_defined_rules)}")
    print(f"Total Rules Tested:  {len(tested_rules)}")
    print(f"Coverage:           {((len(all_defined_rules) - len(missing)) / len(all_defined_rules) * 100):.1f}%")
    
    if missing:
        print("\n[!] Rules Missing Coverage:")
        for fpath, rules in rules_map.items():
            file_missing = rules & missing
            if file_missing:
                print(f"  {fpath}:")
                for r in sorted(file_missing):
                    print(f"    - {r}")
    else:
        print("\n[OK] 100% test coverage achieved!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nova Rules Coverage Auditor")
    parser.add_argument("--rules-dir", default=".", help="Directory containing .nov files")
    parser.add_argument("--tests-dir", default="tests", help="Directory containing YAML tests")
    args = parser.parse_args()
    
    run_audit(args.rules_dir, args.tests_dir)
