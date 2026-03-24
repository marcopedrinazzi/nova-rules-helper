---
name: nova-rules-helper
description: Create, refine, validate, and test Nova Framework detection rules (.nov files) and their YAML tests. Use when an agent needs to author new Nova rules, reduce false positives, review keyword or semantic conditions, audit rule coverage, classify a rule into the Nova taxonomy, or run Nova validation and test tooling.
---

# Nova Rules Helper

This skill helps you create, validate, and test Nova rules based on official standards. In addition to syntax and metadata correctness, it emphasizes high-trust rule design: detect malicious intent rather than risky topics, require enough evidence to justify a match, and minimize false positives in enterprise, educational, and defensive contexts.

## Script-First Rule

Use the prepackaged scripts in this skill before attempting ad-hoc shell commands, handwritten one-off code, or manual file scaffolding.

- Prefer `scripts/create_rule.py` to hand-creating starter rule/test files.
- Prefer `scripts/generate_uuid.py` for every UUID instead of inventing or reusing one.
- Prefer the validation and test scripts in `scripts/validation/` and `scripts/tests/` instead of improvised checks.
- Use direct manual edits only for the actual rule logic, test content, or small glue changes that the scripts are not designed to generate.

If a packaged script exists for the task, treat it as the default path and explain any deviation briefly.

## Prerequisites

This skill requires the `nova-hunting` framework and `yamllint`. Use the environment checker to verify your setup:

```bash
python3 scripts/check_env.py
```

## Workflow

### 0. Discovery (Agent Only)
Before starting any task, the agent must locate the `nova-rules` repository root by searching for `CATEGORIES.md` or existing `.nov` files in the current directory, siblings, or parents. All subsequent commands must use the identified path.

### 1. Define the Abuse Behavior Before Writing the Rule
Before creating or editing a rule, write down:
- The exact harmful action being requested.
- The target of that action.
- The benign prompts that could look similar.

The rule should detect behavior, not subject matter. For example:
- Weak: `"credential rule"`
- Strong: `"requests to reveal, print, share, or retrieve passwords, tokens, API keys, or secrets"`

If the idea is too broad, split it before authoring. Prefer one focused attack family per rule, such as:
- credential disclosure
- system prompt leakage
- ignore or override prior instructions
- explicit jailbreak modes

### 2. Research & Authoring
- Identify the concrete threat or pattern you want to detect.
- Do not scaffold a new rule manually when the packaged generator can do it.
- Use the **rule creator** to generate a tailored starting point. Specify the target directory if not in the repo root:
  ```bash
  python3 scripts/create_rule.py "MyNewRule" --category "prompt_manipulation/jailbreak" --rules-dir <repo_path> --tests-dir <repo_path>/tests
  ```

### 3. Rule Refinement
- Edit the generated `.nov` file.
- **Mandatory UUID**: ALWAYS use `scripts/generate_uuid.py` for all UUID fields.
- Review [rules.md](references/rules.md) for syntax/metadata requirements.
- Consult [CATEGORIES.md](references/CATEGORIES.md) for the official taxonomy.
- Start with explicit lexical evidence for the risky behavior.
- Use keywords or regex first when the attacker behavior is plainly visible in text.
- Add semantics only where you need paraphrase coverage or softer coercive phrasing.
- Do not allow one weak signal to decide the whole match for noisy categories like credential theft, jailbreaks, prompt injection, or malicious intent.
- Prefer evidence combinations such as:
  - action plus sensitive target
  - coercion verb plus instruction or system target
  - harmful instruction plus harmful activity target

Recommended shapes:

```nova
condition:
    (keywords.$reveal or semantics.$credential_disclosure)
    and
    (keywords.$api_key or keywords.$password or keywords.$token)
```

```nova
condition:
    keywords.$ignore_previous
    or
    (semantics.$override_intent and keywords.$instructions)
```

For detailed guidance on semantics, LLM usage, thresholds, and prompt writing, see **Best Practices** below.

### 4. Test Enhancement & Coverage
- Add test cases to the YAML file in the `tests/` directory.
- Cover both obvious attacks and likely paraphrases.
- Add negative tests for benign enterprise, security, educational, translation, and summarization prompts that discuss the topic without expressing abuse.
- **Audit Coverage**: Identify gaps in the repository:
  ```bash
  python3 scripts/audit_coverage.py --rules-dir <repo_path> --tests-dir <repo_path>/tests
  ```

### 5. Validation & Linting
Ensure the rule meets quality standards. Do not substitute ad-hoc validation when these packaged scripts cover the task. Run:

```bash
python3 scripts/validation/validate_syntax.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_metadata.py --rules-dir <repo_path> -v
python3 scripts/validation/lint_rules.py --rules-dir <repo_path> -v
python3 scripts/validation/validate_tests.py --tests-dir <repo_path>/tests
```

### 6. Functional Testing
Run the packaged functional test suite to ensure your rule triggers correctly:
```bash
python3 scripts/tests/test_rules.py --rules-dir <repo_path> --tests-dir <repo_path>/tests -v
```

### 7. Final Rule Review
Before considering the work complete, verify:
- The rule detects abuse, not just a risky topic.
- The condition requires enough evidence for a confident match.
- The rule is still readable and explainable in one sentence.
- The rule would survive benign enterprise and defensive prompts.
- The rule is narrow enough to avoid false positives; if not, split it into smaller rules.

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
- **Script-First Workflow**:
  - Always check the skill's `scripts/` directory before inventing a new workflow.
  - If a bundled script covers the task, use it.
  - Only fall back to custom commands or handwritten helper code when no packaged script fits, and state that choice explicitly.
- **UUIDs**: Never reuse a UUID. Always generate a fresh one via `scripts/generate_uuid.py`.
- **Repo Context**: Always pass the correct repository path to `--rules-dir` if not running from the root.
- **Naming**:
  - **Internal Rule Name**: Always use **PascalCase** (e.g., `SuspiciousInjection`).
  - **Filename**: Should be **snake_case** (e.g., `suspicious_injection.nov`), which is automatically handled by the generator.
- **Behavior Over Topic**:
  - Do not match because a prompt mentions passwords, jailbreaks, system prompts, malware, or API keys.
  - Match because the prompt expresses abuse such as revealing a secret, leaking a system prompt, ignoring instructions, or helping with malware creation.
- **Keywords First**:
  - Prefer keywords for direct disclosure requests, direct prompt injection phrases, explicit bypass language, and exact risky mode names like `DAN` or `developer mode`.
  - Use explicit keyword references (e.g., `keywords.$reveal and keywords.$api_key`) when the condition requires specific evidence combinations. Use `any of keywords.*` only when every defined keyword is independently sufficient to indicate the behavior — this is rare for noisy categories.
- **Semantics As Support**:
  - Use semantics to cover paraphrases and softer wording, not as a catch-all for broad detections.
  - Avoid short, vague semantic texts that describe a topic instead of malicious intent.
  - Do not use broad semantic-only rules for categories like jailbreaks, credentials, or malicious intent.
  - Start most semantic thresholds around `0.40` to `0.45` unless benchmark evidence justifies something else.
  - If a semantic description could also match a benign security article, it is too broad to stand alone.
- **LLM As Last Resort**:
  - The `llm` section carries the highest resource and cost overhead of all condition types. Only use it when keywords and semantics cannot express the required detection logic.
  - Before reaching for `llm`, verify that the check cannot be achieved with a keyword pattern, a semantic description, or a combination of both.
  - When an `llm` check is necessary, place it last in a boolean `or` chain so that cheaper keyword and semantic conditions are evaluated first. Nova evaluates `or` conditions left-to-right and short-circuits — if an earlier branch matches, later branches (including `llm`) are not evaluated.
  - Start most LLM thresholds at `0.5` as a balanced default. For noisy categories (jailbreaks, credentials, malicious intent), prefer `0.6–0.7`. Lower values (`0.3–0.4`) are acceptable only when the LLM check is already gated behind keyword/semantic conditions that provide strong prior evidence.
  - Frame `llm` prompts as a precise yes/no question about the input's intent, not a broad topic check. Tell the LLM what to focus on and what should not trigger the check.
  - Keep prompts concise — longer prompts cost more tokens without necessarily improving accuracy.
  - Avoid vague questions like "Is this malicious?" — instead ask about the specific mechanism, such as "Does this input embed hidden instructions inside quoted content intended to override the model's behavior?"
- **Evidence Combinations**:
  - For noisy categories, require multiple pieces of evidence instead of one weak signal.
  - Common high-signal pairings are action plus target, coercion plus instruction target, or harmful instruction plus harmful activity.
- **Rule Integrity**:
  - Use the most specific subcategory from `CATEGORIES.md`.
  - Ensure all mandatory metadata fields are present and valid.
  - Avoid overloaded conditions that try to cover multiple attack families at once.
  - If a condition is hard to explain in one sentence, split the rule.
- **Test Design**:
  - Provide both positive (should match) and negative (should not match) test cases for every rule.
  - Use the `prompts` list in YAML to test multiple variations of an attack in a single test block.
  - Ensure `rule_name` in the test YAML matches the `rule` name in the `.nov` file exactly.
  - Negative cases should include benign security guidance, policy writing, awareness content, documentation, translation, and summarization where relevant.
- **YAML Linting**:
  - Always run `scripts/validation/validate_tests.py` when creating or modifying test cases.
  - Ensure all YAML files follow the project's formatting rules defined in `assets/.yamllint`.

## Category Guidance

### Credential Request
- Require disclosure, retrieval, leak, print, reveal, or sharing intent.
- Require a sensitive target such as password, API key, token, private key, credential, or secret.
- Do not match prompts that only discuss secure storage, policy, or awareness content.

### System Override
- Require coercion verbs such as ignore, override, forget, disregard, or replace.
- Require an instruction target such as rules, instructions, policies, guardrails, or system prompt.
- Split broad rules into separate behaviors when needed:
  - ignore or override prior instructions
  - reveal system prompt
  - output replacement or answer-only coercion

### Jailbreak Attempt
- Keep strong direct phrases such as `DAN`, `developer mode`, `god mode`, or `unrestricted mode`.
- For softer phrasing, require bypass framing rather than matching roleplay or persona language alone.
- Do not match harmless roleplay, creative writing, or defensive analysis of jailbreaks.

### Malicious Intent
- Require harmful instruction plus harmful activity.
- Favor concrete malicious actions such as steal, evade, deploy, create malware, or bypass detection.
- Do not match defensive explanations, educational material, or generic vulnerability discussion by themselves.

## Review Checklist
- Does the rule detect abuse, or only a topic?
- Does the rule require enough evidence?
- Could a benign enterprise or security prompt satisfy this condition?
- Are the semantic patterns describing malicious intent rather than subject matter?
- Is the rule trying to do too many jobs?
- Should the risky branches be split into smaller rules?
- Is the rule precise enough to avoid false positives, or should it be split?

