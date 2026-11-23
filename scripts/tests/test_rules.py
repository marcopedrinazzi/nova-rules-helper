#!/usr/bin/env python3
"""
Nova Rule Test Runner

This script is the primary tool for functionally testing Nova rules. It is designed to
be run from the command line and offers a flexible way to validate the behavior of
rules against a set of predefined test cases.

The script works by loading test cases from YAML files located in the `tests/`
directory. Each test case defines a prompt and an expected outcome (i.e., whether
a rule should match or not). The script then runs the Nova matching engine against
each prompt and compares the actual outcome with the expected one.

Decision tests evaluate prompts through a live model only with --decision-testing.
Required Decision checks are otherwise skipped. Optional decision_state supplies
caller context; expected_match: null expects an incomplete live evaluation.

The test runner also supports:
- **Keyword Matching**: The default and most common type of matching.
- **Semantic Matching**: For rules that use semantic vectors for matching.
- **LLM-based Matching**: For rules that require a Large Language Model for
  evaluation. This is an optional feature that can be enabled via the
  command line.

By default, LLM-based evaluation is skipped to avoid the need for API keys in
CI/CD environments. To enable it, use the `--llm-testing` flag and specify an
LLM provider with `--llm-provider`.
"""

import os
import sys
import copy
import argparse
import json
from typing import Dict, Any, List, Tuple, Optional
import yaml
from colorama import init as colorama_init
from nova.core.parser import NovaRuleFileParser, NovaParserError
from nova.core.matcher import NovaMatcher
from nova.core.rules import NovaRule
from nova.core.decision import NovaEvaluationError
from nova.evaluators.decision.config import DecisionConfig
from nova.evaluators.decision.factory import create_decision_evaluator
from nova.utils.config import get_config
from nova.evaluators.base import LLMEvaluator
from nova.evaluators.semantics import DefaultSemanticEvaluator
from nova.evaluators.llm import get_validated_evaluator

# Allow imports from sibling validation package
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
from ci_utils import print_pass, print_fail, print_warn, print_header, print_summary

# Shared semantic evaluator instance (loaded once, reused across all tests)
_semantic_evaluator = None
_llm_evaluator = None


def get_semantic_evaluator() -> DefaultSemanticEvaluator:
    """Lazy-load and return a shared semantic evaluator."""
    global _semantic_evaluator
    if _semantic_evaluator is None:
        _semantic_evaluator = DefaultSemanticEvaluator()
    return _semantic_evaluator


def load_test_cases(tests_dir: str) -> List[Dict[str, Any]]:
    """
    Load all YAML test case files from tests_dir.
    Returns flat list of test case dicts with source metadata added.

    Supports both single ``prompt`` and multi ``prompts`` formats.
    A test with ``prompts: [p1, p2]`` is expanded into separate test
    cases named "<name> [1/2]", "<name> [2/2]".
    """
    test_cases = []
    for root, dirs, files in os.walk(tests_dir):
        for fname in sorted(files):
            if fname.endswith((".yaml", ".yml")) and not fname.startswith("."):
                fpath = os.path.join(root, fname)
                with open(fpath, "r") as f:
                    data = yaml.safe_load(f)
                
                if not isinstance(data, dict):
                    raise ValueError(f"{fpath}: test file must be a mapping")
                if "tests" not in data:
                    raise ValueError(f"{fpath}: missing mandatory tests field")
                if not isinstance(data["tests"], list):
                    raise ValueError(f"{fpath}: tests must be a list")

                rule_file = data.get("rule_file", "")
                
                for tc in data["tests"]:
                    if not isinstance(tc, dict):
                        raise ValueError(f"{fpath}: each test must be a mapping")
                    for field in ("name", "rule_name"):
                        if not isinstance(tc.get(field), str) or not tc[field].strip():
                            raise ValueError(f"{fpath}: {field} must be a nonempty string")
                    if not isinstance(rule_file, str) or not rule_file.strip():
                        raise ValueError(f"{fpath}: rule_file must be a nonempty string")
                    if "expected_match" not in tc or (tc["expected_match"] is not None and type(tc["expected_match"]) is not bool):
                        raise ValueError(f"{fpath}: expected_match must be true, false, or null")
                    if ("prompt" in tc) == ("prompts" in tc):
                        raise ValueError(f"{fpath}: provide exactly one of prompt or prompts")
                    inputs = tc.get("prompts") if "prompts" in tc else [tc["prompt"]]
                    if not isinstance(inputs, list) or not inputs or any(not isinstance(value, str) or not value.strip() for value in inputs):
                        raise ValueError(f"{fpath}: prompts must contain nonempty strings")
                    tc["_source_yaml"] = fpath
                    tc["_rule_file"] = rule_file

                    # Expand multi-prompt test cases
                    prompts = tc.get("prompts")
                    if prompts and isinstance(prompts, list):
                        base_name = tc.get("name")
                        for i, prompt in enumerate(prompts, 1):
                            expanded = copy.deepcopy(tc)
                            expanded["prompt"] = prompt
                            expanded["name"] = f"{base_name} [{i}/{len(prompts)}]"
                            expanded.pop("prompts", None)
                            test_cases.append(expanded)
                    else:
                        test_cases.append(tc)
    return test_cases


def load_rules_from_file(
    rule_file: str, rules_dir: str
) -> Dict[str, NovaRule]:
    """
    Parse a rule file and return a dict of rule_name -> NovaRule.
    """
    fpath = os.path.join(rules_dir, rule_file)
    parser = NovaRuleFileParser()
    rules = parser.parse_file(fpath)
    return {rule.name: rule for rule in rules}


def run_test(
    rule: NovaRule,
    prompt: str,
    expected_match: Optional[bool],
    llm_evaluator: Optional[LLMEvaluator] = None,
    verbose: bool = False,
    *, decision_config=None, decision_state=None, decision_evaluator=None,
) -> Tuple[str, str]:
    """
    Run a single test case against a rule.

    This function orchestrates the execution of a single test case. It initializes
    the `NovaMatcher` with the appropriate evaluators (keyword, semantic, and
    optionally LLM) and then runs the matcher against the provided prompt.

    The function returns a status string ("pass", "fail", or "skip") and a
    detailed message explaining the outcome. A test is marked as "skip" if it
    requires LLM evaluation but no LLM evaluator is provided.

    Args:
        rule: The `NovaRule` object to be tested.
        prompt: The input prompt to test against the rule.
        expected_match: True/False for a completed result, or None for incomplete.
        llm_evaluator: An optional `LLMEvaluator` instance. If provided, LLM-based
                       evaluation will be performed.
        verbose: If `True`, includes additional details in the output message.
        decision_config: Runtime Decision options; disabled by default.
        decision_state: Optional caller-supplied context for the scan.
        decision_evaluator: Shared evaluator for live Decision testing.

    Returns:
        A tuple containing the test status ("pass", "fail", or "skip") and a
        detailed message about the test result.
    """
    if expected_match is not None and type(expected_match) is not bool:
        return "fail", "expected_match must be true, false, or null (incomplete)"
    if isinstance(decision_config, DecisionConfig):
        resolved_config = decision_config
    else:
        options = dict(decision_config or {})
        options.setdefault("enabled", False)
        resolved_config = DecisionConfig.resolve(options) if options["enabled"] else DecisionConfig(**options)
    matcher = NovaMatcher(
        rule,
        semantic_evaluator=get_semantic_evaluator() if rule.semantics else None,
        llm_evaluator=llm_evaluator,
        create_llm_evaluator=True if llm_evaluator else False,
        decision_config=resolved_config, decision_evaluator=decision_evaluator,
    )
    try:
        result = matcher.check_prompt(prompt, decision_state=decision_state)
        causes = []
    except NovaEvaluationError as error:
        result, causes = error.result, error.causes

    warnings = result.get("debug", {}).get("evaluation_warnings", [])
    if warnings and "evaluation_complete" not in result:
        if all(("no " in warning and "evaluator is available" in warning) or "skipped LLM evaluation" in warning for warning in warnings):
            return "skip", "; ".join(warnings)
        causes = causes or warnings
    actual_match = result["matched"]
    if causes or result.get("evaluation_complete") is False:
        actual_match = None
        causes = causes or [entry.rsplit(": ", 1)[-1] for entry in result.get("unresolved", [])]
        if causes and set(causes) <= {
            "disabled", "skipped", "llm_not_configured", "llm_unavailable", "semantics_not_configured",
        }:
            return "skip", (
                f"required checks were not run ({','.join(sorted(set(causes)))}); "
                "enable/configure their evaluators with --decision-testing or --llm-testing"
            )

    # Build detail string with all available scores
    detail = f"matched={actual_match}, expected={expected_match}"
    if causes:
        detail += f", incomplete={','.join(sorted(set(causes)))}"
    if verbose and result.get("decision_results"):
        detail += f", decision={json.dumps(result['decision_results'], ensure_ascii=False)}"
    if verbose and result.get("matching_keywords"):
        detail += f", keywords={result['matching_keywords']}"
    if verbose and result.get("semantic_scores"):
        sem_parts = []
        for k, v in result["semantic_scores"].items():
            sem_parts.append(f"{k}={v:.3f}")
        detail += f", sem={{{', '.join(sem_parts)}}}"
    if verbose and result.get("llm_scores"):
        llm_parts = []
        for k, v in result["llm_scores"].items():
            llm_parts.append(f"{k}={v:.3f}")
        detail += f", llm={{{', '.join(llm_parts)}}}"

    if actual_match == expected_match:
        return "pass", detail

    return "fail", detail


def run(
    rules_dir: str,
    tests_dir: str,
    verbose: bool = False,
    llm_testing: bool = False,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    decision_testing: bool = False,
    decision_provider: Optional[str] = None,
    decision_model: Optional[str] = None,
    decision_host: Optional[str] = None,
    config: Optional[str] = None,
    **kwargs,
) -> Tuple[int, Dict[str, Any]]:
    """
    Execute the main logic for rule testing.

    This function serves as the main entry point for the test runner. It handles
    the discovery and loading of test cases, initialization of the LLM evaluator
    (if requested), and the iteration over all test cases.

    The function aggregates the results of all test cases and prints a summary
    at the end. It returns an exit code (0 for success, 1 for failure) and a
    dictionary containing the counts of passed, failed, and skipped tests.

    Args:
        rules_dir: The directory containing the `.nov` rule files.
        tests_dir: The directory containing the YAML test case files.
        verbose: If `True`, enables detailed per-test logging.
        llm_testing: If `True`, enables LLM-based evaluation.
        llm_provider: The name of the LLM provider to use (e.g., "openai").
        llm_model: The name of the specific LLM model to use.
        **kwargs: Additional keyword arguments.

    Returns:
        A tuple containing the exit code and a dictionary with the test results.
    """
    global _llm_evaluator
    _llm_evaluator = None
    options = {"enabled": decision_testing}
    options.update({key: value for key, value in (("provider", decision_provider), ("model", decision_model),
                                                 ("host", decision_host)) if value is not None})
    try:
        if config:
            get_config(config)
        decision_config = DecisionConfig.resolve(options) if decision_testing else DecisionConfig()
        decision_evaluator = create_decision_evaluator(decision_config) if decision_testing else None
    except (OSError, ValueError, TypeError) as error:
        print_fail(f"Invalid configuration: {error}")
        return 1, {"passed": 0, "failed": 1, "skipped": 0}
    rules_dir = os.path.abspath(rules_dir)
    tests_dir = os.path.abspath(tests_dir)

    if not os.path.isdir(tests_dir):
        print_fail(f"Tests directory not found: {tests_dir}")
        return 1, {"passed": 0, "failed": 1, "skipped": 0}

    # Setup LLM evaluator if requested
    if llm_testing:
        if not llm_provider:
            print_fail("LLM testing enabled, but --llm-provider is not specified.")
            return 1, {"passed": 0, "failed": 1, "skipped": 0}
        try:
            _llm_evaluator = get_validated_evaluator(
                llm_provider, model=llm_model, verbose=verbose
            )
            print_header(f"LLM testing enabled with {llm_provider} (model: {llm_model or 'default'})")
        except ValueError as e:
            print_fail(f"Failed to initialize LLM evaluator: {e}")
            return 1, {"passed": 0, "failed": 1, "skipped": 0}

    try:
        test_cases = load_test_cases(tests_dir)
    except (OSError, yaml.YAMLError, ValueError) as error:
        print_fail(f"Cannot load test cases: {error}")
        return 1, {"passed": 0, "failed": 1, "skipped": 0}
    if not test_cases:
        print_fail("No runnable YAML test cases found")
        return 1, {"passed": 0, "failed": 1, "skipped": 0}

    print_header(f"Rule Testing: {len(test_cases)} test case(s)")

    # Cache parsed rule files
    rule_cache: Dict[str, Dict[str, NovaRule]] = {}

    passed = 0
    failed = 0
    skipped = 0

    for tc in test_cases:
        rule_file = tc.get("_rule_file", "")
        rule_name = tc.get("rule_name", "")
        test_name = tc.get("name")
        prompt = tc.get("prompt", "")
        expected_match = tc.get("expected_match")

        if not test_name:
            source = os.path.basename(tc.get("_source_yaml", "unknown"))
            print_fail(f"Test case in {source} is missing mandatory 'name' field")
            failed += 1
            continue

        if not rule_file:
            print_fail(f"{test_name}: missing mandatory 'rule_file' field")
            failed += 1
            continue

        if not rule_name:
            print_fail(f"{test_name}: missing mandatory 'rule_name' field")
            failed += 1
            continue

        if not prompt:
            print_fail(f"{test_name}: missing mandatory 'prompt' field")
            failed += 1
            continue

        if "expected_match" not in tc or (expected_match is not None and type(expected_match) is not bool):
            print_fail(f"{test_name}: expected_match must be present and be true, false, or null")
            failed += 1
            continue

        # Load rule file if not cached
        if rule_file not in rule_cache:
            try:
                rule_cache[rule_file] = load_rules_from_file(rule_file, rules_dir)
            except (NovaParserError, FileNotFoundError) as e:
                print_fail(f"{test_name}: Cannot load rule file '{rule_file}': {e}")
                failed += 1
                continue

        # Find the specific rule
        rules_in_file = rule_cache[rule_file]
        if rule_name not in rules_in_file:
            print_fail(
                f"{test_name}: Rule '{rule_name}' not found in '{rule_file}'. "
                f"Available: {', '.join(rules_in_file.keys())}"
            )
            failed += 1
            continue

        rule = rules_in_file[rule_name]
        if "decision_answers" in tc:
            print_fail(f"{test_name}: decision_answers is unsupported; test the prompt with --decision-testing")
            failed += 1
            continue
        try:
            status, detail = run_test(
                rule, prompt, expected_match, llm_evaluator=_llm_evaluator, verbose=verbose,
                decision_config=decision_config, decision_state=tc.get("decision_state"),
                decision_evaluator=decision_evaluator,
            )
        except (ValueError, TypeError) as error:
            status, detail = "fail", f"Invalid test input: {error}"

        if status == "skip":
            skipped += 1
            if verbose:
                print_warn(f"{test_name} ({rule_name}): {detail}")
        elif status == "pass":
            passed += 1
            if verbose:
                print_pass(f"{test_name} ({rule_name}): {detail}")
        else:
            failed += 1
            print_fail(f"{test_name} ({rule_name}): {detail}")

    print_summary(passed, failed, skipped, third_label="skipped")
    exit_code = 0 if failed == 0 else 1
    return exit_code, {"passed": passed, "failed": failed, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(
        description="Run YAML-driven tests against Nova rules, including optional live Decision models."
    )
    parser.add_argument(
        "--rules-dir", default=".",
        help="Path to directory containing .nov rule files (default: current dir)"
    )
    parser.add_argument(
        "--tests-dir", default="tests",
        help="Path to directory containing YAML test case files (default: tests/)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show per-test details including skipped tests"
    )
    parser.add_argument(
        "--llm-testing", action="store_true",
        help="Enable LLM-based evaluation for tests that require it"
    )
    parser.add_argument(
        "--llm-provider", type=str, default=None,
        choices=["openai", "anthropic", "azure", "ollama", "groq", "openrouter"],
        help="Specify the LLM provider to use (e.g., 'openai', 'ollama')"
    )
    parser.add_argument(
        "--llm-model", type=str, default=None,
        help="Specify the model name for the LLM provider"
    )
    parser.add_argument("--decision-testing", action="store_true", help="Enable live Decision evaluation of test prompts")
    parser.add_argument("--decision-provider", choices=["openrouter", "ollama"], help="Decision provider")
    parser.add_argument("--decision-model", help="Decision model ID (required for Ollama)")
    parser.add_argument("--decision-host", help="Ollama Decision server URL")
    parser.add_argument("--config", help="Nova configuration file, including API keys")
    args = parser.parse_args()

    colorama_init()
    exit_code, _ = run(
        args.rules_dir,
        tests_dir=args.tests_dir,
        verbose=args.verbose,
        llm_testing=args.llm_testing,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        decision_testing=args.decision_testing,
        decision_provider=args.decision_provider,
        decision_model=args.decision_model,
        decision_host=args.decision_host,
        config=args.config,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
