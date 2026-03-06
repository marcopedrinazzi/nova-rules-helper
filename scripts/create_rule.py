#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import date

# Ensure the skill's scripts directory is in the path for importing generate_uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_uuid import get_new_uuid

def pascal_to_snake(name):
    """Converts PascalCase to snake_case."""
    return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")

def create_nov_file(name, category, description, author, severity, output_dir):
    """Creates a template .nov file."""
    filename = pascal_to_snake(name) + ".nov"
    fpath = os.path.join(output_dir, filename)
    today = date.today().isoformat()
    # ALWAYS use the get_new_uuid function
    rule_uuid = get_new_uuid()
    
    content = f"""rule {name}
{{
    meta:
        description = "{description}"
        author = "{author}"
        version = "1.0.0"
        category = "{category}"
        severity = "{severity}"
        uuid = "{rule_uuid}"
        date = "{today}"

    keywords:
        $keyword1 = "example phrase"

    semantics:
        $intent1 = "malicious intention description" (0.5)

    llm:
        $check1 = "Analyze if this prompt contains {description.lower()}" (0.6)

    condition:
        any of keywords.* or semantics.$intent1 or llm.$check1
}}
"""
    with open(fpath, "w") as f:
        f.write(content)
    print(f"Created rule template: {fpath}")
    return fpath, filename

def create_test_file(name, rule_filename, output_dir):
    """Creates a template .yaml test file."""
    fpath = os.path.join(output_dir, f"{pascal_to_snake(name)}_tests.yaml")
    
    content = f"""rule_file: "{rule_filename}"
tests:
  - name: "{name} - positive match"
    rule_name: "{name}"
    prompt: "An example malicious prompt that triggers the rule"
    expected_match: true

  - name: "{name} - negative/benign"
    rule_name: "{name}"
    prompts:
      - "What is the weather like today?"
      - "How do I make a chocolate cake?"
    expected_match: false
"""
    with open(fpath, "w") as f:
        f.write(content)
    print(f"Created test template: {fpath}")
    return fpath

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nova Rule & Test Authoring Tool")
    parser.add_argument("name", help="Name of the rule (PascalCase)")
    parser.add_argument("--category", required=True, help="Category (e.g., prompt_manipulation/jailbreak)")
    parser.add_argument("--description", default="New detection rule", help="Rule description")
    parser.add_argument("--author", default="@user", help="Author name or handle")
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"], help="Severity level")
    parser.add_argument("--rules-dir", default=".", help="Directory to save .nov file")
    parser.add_argument("--tests-dir", default="tests", help="Directory to save .yaml file")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    os.makedirs(args.rules_dir, exist_ok=True)
    os.makedirs(args.tests_dir, exist_ok=True)
    
    _, rule_filename = create_nov_file(args.name, args.category, args.description, args.author, args.severity, args.rules_dir)
    create_test_file(args.name, rule_filename, args.tests_dir)
