---
name: nova-rules-helper
description: Facilitates the creation, validation, and testing of Nova rules (.nov files). Use when you need to audit test coverage, write new detection rules, or verify existing rules using the Nova Framework.
---

# Nova Rules Helper

This skill helps you create, validate, and test Nova rules based on official standards.

## Prerequisites

This skill requires the `nova-hunting` framework and `yamllint`. Use the environment checker to verify your setup:

```bash
python3 scripts/check_env.py
```

## Workflow

### 0. Discovery (Agent Only)
Before starting any task, the agent must locate the `nova-rules` repository root by searching for `CATEGORIES.md` or existing `.nov` files in the current directory, siblings, or parents. All subsequent commands must use the identified path.

### 1. Research & Authoring
- Identify the threat or pattern you want to detect.
- Use the **rule creator** to generate a tailored starting point. Specify the target directory if not in the repo root:
  ```bash
  python3 scripts/create_rule.py "MyNewRule" --category "prompt_manipulation/jailbreak" --rules-dir <repo_path> --tests-dir <repo_path>/tests
  ```

### 2. Rule Refinement
- Edit the generated `.nov` file.
- **Mandatory UUID**: ALWAYS use `scripts/generate_uuid.py` for all UUID fields.
- Review [rules.md](references/rules.md) for syntax/metadata requirements.
- Consult [CATEGORIES.md](references/CATEGORIES.md) for the official taxonomy.

### 3. Test Enhancement & Coverage
- Add test cases to the YAML file in the `tests/` directory.
- **Audit Coverage**: Identify gaps in the repository:
  ```bash
  python3 scripts/audit_coverage.py --rules-dir <repo_path> --tests-dir <repo_path>/tests
  ```

### 4. Validation & Linting
Ensure the rule meets quality standards. Run these using the prepackaged scripts:

```bash
python3 scripts/validation/validate_syntax.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_metadata.py --rules-dir <repo_path> -v
python3 scripts/validation/lint_rules.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_tests.py --tests-dir <repo_path>/tests
```

### 5. Functional Testing
Run the test suite to ensure your rule triggers correctly:
```bash
python3 scripts/tests/test_rules.py --rules-dir <repo_path> --tests-dir <repo_path>/tests -v
```

## Helper Scripts
(Located in the skill's `scripts/` directory)
- `scripts/audit_coverage.py`: Compares `.nov` rules vs. YAML tests.
- `scripts/check_env.py`: Verifies dependencies.
- `scripts/create_rule.py`: Generates tailored rule/test templates.
- `scripts/generate_uuid.py`: Mandatory tool for fresh UUIDs.

## Core Validation Scripts (Prepackaged Official Tools)
- `scripts/validation/validate_syntax.py`
- `scripts/validation/validate_metadata.py`
- `scripts/validation/lint_rules.py`
- `scripts/validation/validate_tests.py` (New: YAML Linting for tests)
- `scripts/tests/test_rules.py`

## Best Practices
- **UUIDs**: Never reuse a UUID. Always generate a fresh one via `scripts/generate_uuid.py`.
- **Repo Context**: Always pass the correct repository path to `--rules-dir` if not running from the root.
- **Naming**:
  - **Internal Rule Name**: Always use **PascalCase** (e.g., `SuspiciousInjection`).
  - **Filename**: Should be **snake_case** (e.g., `suspicious_injection.nov`), which is automatically handled by the generator.
- **Rule Integrity**:
  - Use the most specific subcategory from `CATEGORIES.md`.
  - Ensure all mandatory metadata fields are present and valid.
  - Avoid overly broad conditions that cause false positives.
- **Test Design**:
  - Provide both positive (should match) and negative (should not match) test cases for every rule.
  - Use the `prompts` list in YAML to test multiple variations of an attack in a single test block.
  - Ensure `rule_name` in the test YAML matches the `rule` name in the `.nov` file exactly.
- **YAML Linting**:
  - Always run `scripts/validation/validate_tests.py` when creating or modifying test cases.
  - Ensure all YAML files follow the project's formatting rules defined in `assets/.yamllint`.
