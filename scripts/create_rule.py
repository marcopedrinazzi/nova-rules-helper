#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import date

# Ensure the skill's scripts directory is in the path for importing generate_uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_uuid import get_new_uuid

DECISION_TEMPLATES = {
    "noul": '''        $check = noul QUESTION {
            true = "An active instruction to carry out the described behavior"
            false = "Ordinary work or discussion without a request to execute the behavior"
            threshold = 0.75
        }''',
    "choice": '''        $check = choice QUESTION {
            options = {
                active = "An active instruction to carry out the described behavior"
                discussion = "Quotation or analysis without a request to execute the behavior"
                other = "An unrelated request"
            }
            match = ["active"]
            min_confidence = 0.60
        }''',
    "score": '''        $check = score QUESTION {
            levels = [
                "An unrelated request",
                "Discussion without a request to execute the behavior",
                "An implicit request to carry out the described behavior",
                "An explicit request to carry out the described behavior"
            ]
            threshold = 2.0
            min_confidence = 0.60
        }''',
}


def pascal_to_snake(name):
    """Converts PascalCase to snake_case."""
    import re
    # Handle consecutive capitals (e.g., ABCRule -> abc_rule)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()

def create_nov_file(name, category, description, author, severity, output_dir, decision=None):
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
        $intent1 = "describe the specific malicious intent to detect" (THRESHOLD)

    // Add llm section only if keywords and semantics cannot cover the detection.
    // Use a precise yes/no question, not a broad topic check. Set model temperature deliberately.
    // See SKILL.md Best Practices > LLM As Last Resort for guidance.

    condition:
        keywords.$keyword1 and semantics.$intent1
}}
"""
    if decision:
        questions = {
            "noul": f"Does text actively request this behavior: {description}?",
            "choice": f"How does text relate to this behavior: {description}?",
            "score": f"How directly does text request this behavior: {description}?",
        }
        declaration = DECISION_TEMPLATES[decision].replace("QUESTION", json.dumps(questions[decision]))
        content = content[:content.index("    keywords:")] + "    llm:\n" + declaration + "\n\n    condition:\n        llm.$check\n}\n"
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
    
    parser.add_argument("--decision", choices=["noul", "choice", "score"],
                        help="Generate a starter rule with decision model questions under llm: and prompt tests")
    args = parser.parse_args()
    
    # Ensure directories exist
    os.makedirs(args.rules_dir, exist_ok=True)
    os.makedirs(args.tests_dir, exist_ok=True)
    
    _, rule_filename = create_nov_file(args.name, args.category, args.description, args.author, args.severity, args.rules_dir, decision=args.decision)
    create_test_file(args.name, rule_filename, args.tests_dir)
