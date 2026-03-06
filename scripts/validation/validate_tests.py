#!/usr/bin/env python3
"""
Nova Test Case Linter
Uses yamllint to verify the formatting and structural integrity of YAML test files.
"""

import os
import sys
import subprocess
import argparse
from typing import Tuple, Dict, Any

from colorama import init as colorama_init
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ci_utils import print_pass, print_fail, print_header, print_summary

def run_yamllint(tests_dir: str, config_path: str = None) -> Tuple[int, str]:
    """Runs yamllint on the specified directory."""
    cmd = ["yamllint", tests_dir]
    if config_path and os.path.exists(config_path):
        cmd.extend(["-c", config_path])
    else:
        # Fallback to a reasonable default if no config is found
        cmd.extend(["-d", "{extends: default, rules: {line-length: disable, document-start: disable}}"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout
    except FileNotFoundError:
        return 127, "Error: yamllint command not found. Please install it with 'pip install yamllint'."

def run(tests_dir: str, config_path: str = None, **kwargs) -> Tuple[int, Dict[str, Any]]:
    """
    Main logic for test linting.
    Returns (exit_code, details_dict).
    """
    tests_dir = os.path.abspath(tests_dir)
    print_header(f"YAML Lint: Scanning tests in {tests_dir}")
    
    if not os.path.isdir(tests_dir):
        print_fail(f"Tests directory not found: {tests_dir}")
        return 1, {"errors": 1, "warnings": 0}

    exit_code, output = run_yamllint(tests_dir, config_path)
    
    if exit_code == 0:
        print_pass("All YAML test files are correctly formatted.")
        return 0, {"errors": 0, "warnings": 0}
    elif exit_code == 127:
        print_fail(output)
        return 1, {"errors": 1, "warnings": 0}
    else:
        print_fail("YAML linting errors found:")
        print(output)
        # Simple heuristic to count errors/warnings from output
        error_count = output.count("error")
        warn_count = output.count("warning")
        print_summary(0, error_count, warn_count)
        return 1, {"errors": error_count, "warnings": warn_count}

def main():
    parser = argparse.ArgumentParser(
        description="Lint Nova YAML test files for formatting and syntax."
    )
    parser.add_argument(
        "--tests-dir", default="tests",
        help="Path to directory containing YAML test files (default: tests/)"
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to .yamllint config file"
    )
    args = parser.parse_args()

    colorama_init()
    
    # Try to find default config in skill's assets/
    config = args.config
    if not config:
        # Resolve path relative to this script
        potential_config = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", ".yamllint"
        )
        if os.path.exists(potential_config):
            config = potential_config

    exit_code, _ = run(args.tests_dir, config_path=config)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
