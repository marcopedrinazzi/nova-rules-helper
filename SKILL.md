---
name: nova-rules-helper
description: Create, refine, validate, and test Nova Framework detection rules (.nov files) and their YAML tests. Use when an agent needs to author new Nova rules, reduce false positives, review keyword, semantic, or decision model conditions, audit rule coverage, classify a rule into the Nova taxonomy, or run Nova validation and test tooling.
---

# Nova Rules Helper

Create, refine, validate, and test focused Nova detections. Detect harmful behavior rather than topic mentions, and check realistic benign look-alikes before handover.

## Use the packaged tools

Use the bundled generator, validators, and runner when they cover the task. Edit rule logic and test content directly; explain any fallback to custom tooling. Generate a UUID with `scripts/generate_uuid.py` once for each new rule, preserve it across revisions, and never assign it to a different rule.

## Workflow

### 1. Locate the rules and check the environment

Find the target `nova-rules` repository using `CATEGORIES.md` or existing `.nov` files in the current directory, siblings, or parents. Pass its path to the tools. This skill requires a `nova-hunting` build supporting decision model checks under `llm:`, even for tests without decision model checks, plus `yamllint`.

```bash
python3 scripts/check_env.py
```

### 2. Define one behavior

Write down the harmful action, its target, and benign prompts that could resemble it. Complete: "This rule fires when the input [one clear behavior]." If the rule covers distinct attack families, split it. Apply this check during refinement too.

### 3. Generate and refine the rule

```bash
python3 scripts/create_rule.py MyNewRule --category prompt_manipulation/jailbreak \
  --rules-dir <repo_path> --tests-dir <repo_path>/tests
```

Use `--decision noul`, `--decision choice`, or `--decision score` for a decision model starter. It starts standalone; refine the question and condition for the intended role. Replace all scaffold evidence and test prompts before evaluation.

Read the relevant parts of [rules.md](references/rules.md):

- [Structure](references/rules.md#rule-structure), [metadata](references/rules.md#metadata-requirements), and [rule requirements](references/rules.md#rule-requirements) for valid files. Choose the most specific category in [CATEGORIES.md](references/CATEGORIES.md).
- [Detection design](references/rules.md#detection-design) for evidence and prompt design.
- [Model roles](references/rules.md#model-roles-and-conditions) to choose standalone, confirmation, or independent fallback. Do not impose a keyword gate automatically.
- [Decision model checks](references/rules.md#decision-model-checks) for `noul`, `choice`, and `score` declarations and answer types.
- [Threshold guidelines](references/rules.md#threshold-guidelines) for semantic, LLM check, and decision model settings.

### 4. Write representative YAML cases

Use the [test format](references/rules.md#rule-testing) and [local false-positive controls](references/rules.md#local-false-positive-controls). Exercise every matching path and likely paraphrases, including benign enterprise, defensive, educational, translation, and summarization contexts where relevant.

For context-dependent decision model checks, provide `decision_state` and test the same action under different approved tasks. The application owns validation of required context. See [Rule testing](references/rules.md#rule-testing) for context, expected outcomes, and provider options.

### 5. Validate and audit coverage

```bash
python3 scripts/validation/validate_syntax.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_metadata.py --rules-dir <repo_path> -v
python3 scripts/validation/lint_rules.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_tests.py --tests-dir <repo_path>/tests
python3 scripts/audit_coverage.py --rules-dir <repo_path> --tests-dir <repo_path>/tests
```

### 6. Run functional tests

```bash
python3 scripts/tests/test_rules.py --rules-dir <repo_path> --tests-dir <repo_path>/tests -v
```

Enable `--decision-testing` for decision model checks and `--llm-testing` for LLM checks; configure the provider/model for each and enable both for mixed rules. Required disabled checks are skipped, so a successful exit alone does not prove they were evaluated. Inspect verbose results and resolve gaps before handover.

### 7. Review and hand over

Report the rules and cases evaluated, model settings, failures, skips, and unresolved outcomes. Claim readiness only when the local false-positive checks pass; incomplete assessments are not nonmatches.
