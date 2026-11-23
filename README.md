# Nova Rules Helper (Agent Skill)

An **LLM Agent Skill** that provides expert-level assistance for authoring, validating, and testing Nova rules. This skill transforms your AI assistant into a **specialized helper** for the [**NOVA Prompt Pattern Matching Framework**](https://github.com/Nova-Hunting/nova-framework), ensuring your Nova detection patterns follow the best practices.

## What This Skill Does

The **nova-rules-helper** equips your LLM agent with the tools and context needed to be your primary assistant in detection engineering for Nova rules:

- **Intelligent Rule Authoring**: Helps you draft Nova rules using keywords, semantics, LLM checks, and decision models through typed questions under `llm:`.
- **Validation & Quality Control**: Automatically checks your work for syntax errors, metadata gaps (UUIDs, severity), and taxonomy alignment.
- **YAML Test Linting**: Ensures all YAML test cases are correctly formatted and follow the project's style guide using `yamllint`.
- **Coverage Auditing**: Identifies rules without runnable YAML cases and validates their rule file/name references. This checks test presence; run the functional tests to verify outcomes.
- **Functional Verification**: Runs rule tests across keywords, semantic similarity, LLM evaluation, and explicitly enabled live decision models.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nova-rules-helper.git
cd nova-rules-helper

# Install required dependencies
pip install -r requirements.txt

# Copy to your agent's skills folder (gemini in the example)
cp -r . ~/.gemini/skills/nova-rules-helper
```

Use a `nova-hunting` build supporting typed questions under `llm:`. Run `python3 scripts/check_env.py` to verify compatibility before using the helpers.

## Usage

Once installed, your agent acts as a helper-expert. You can initiate tasks using simple requests:

### Use Case 1: Intelligent Rule Authoring
> "Help me create a rule for a DAN-style jailbreak attempt"

The agent transforms your request into a Nova rule with tailored detection logic and matching YAML tests.
- **Intelligent Drafting**: Executes `scripts/create_rule.py` to generate a Nova rule with specifically designed for the requested threat. The Nova rule is created following the Nova rules best pratices.
- **Test Alignment**: Generates a matching YAML test file for immediate functional verification.

### Use Case 2: Validate & Audit
> "Review my rules in the ./rules folder and check for coverage gaps"

The agent uses the helper tools to:
- Validate syntax and metadata of Nova Rules
- List any rules that are missing test cases in the matching `tests/` path.

### Use Case 3: Test Verification
> "Run the tests for the new prompt injection rule I just finished"

The agent executes the test runner and provides a detailed report on:
- Keyword matches.
- Semantic similarity scores.
- LLM confidence levels (if configured).

### Decision model rule tests

Create a starter rule and YAML prompt tests. Refine the prompts for the behavior being detected:

```bash
python3 scripts/create_rule.py InstructionOverride \
  --category prompt_manipulation/jailbreak --decision noul \
  --rules-dir ./rules --tests-dir ./tests
python3 scripts/tests/test_rules.py --rules-dir ./rules --tests-dir ./tests -v
```

Choose `noul`, `choice`, or `score` with `--decision`. Add `--decision-testing`
and select a provider/model to evaluate the prompts. Required Decision checks are
skipped without that flag; see [Rule testing](references/rules.md#rule-testing).

## What's Included

The skill embeds authoritative Nova standards directly into the agent's context:

1. **[Nova Rules Guide](references/rules.md)** — A guide to Nova rules, including quoted checks and typed questions under `llm:`.
2. **[Nova Rules Categories](references/CATEGORIES.md)** — This document defines the four main categories and their subcategories for Nova rules, based on the [official Nova taxonomy](https://promptintel.novahunting.ai/taxonomy)
3. **Helper Suite** — Python scripts for automated syntax checking, metadata validation, YAML linting, and coverage auditing

## Core Validation and Testing Scripts
- `scripts/validation/validate_syntax.py`
- `scripts/validation/validate_metadata.py`
- `scripts/validation/lint_rules.py`
- `scripts/validation/validate_tests.py` (YAML formatting check)
- `scripts/tests/test_rules.py` (Functional test runner)

## Contributing

Contributions are welcome! 

## License

Distributed under the MIT License. See `LICENSE` for more information.
