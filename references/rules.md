# NOVA Rules Reference

NOVA is an open-source prompt pattern matching framework that combines keyword detection, semantic similarity, and LLM-based evaluation to analyze and detect malicious or suspicious prompts.

## Rule Structure

Nova rules use a custom `.nov` format. Each rule follows this basic structure:

```nova
rule YourRuleName
{
    meta:
        description = "A clear description of what this rule detects"
        author = "Your Name or @handle"
        version = "1.0.0"
        category = "category/subcategory"
        severity = "medium"
        uuid = "generate-a-fresh-v4-uuid"
        date = "YYYY-MM-DD"
        // Optional fields
        reference = "URL or report name"
        modified = "YYYY-MM-DD"

    keywords:
        $keyword1 = "exact string"
        $keyword2 = /regex_pattern/i

    semantics:
        $concept1 = "semantic description of intent" (0.35)

    llm:
        $check1 = "Natural language instruction for the LLM to verify" (0.5)

    condition:
        any of keywords.* or semantics.$concept1 or llm.$check1
}
```

## Metadata Requirements

All rules must include the following fields in the `meta` section:

| Field | Requirement | Description |
| :--- | :--- | :--- |
| `description` | Required | High-level explanation of the detection goal. |
| `author` | Required | Credit for the rule creator. |
| `version` | Required | Semantic versioning (e.g., `1.0.0`). |
| `category` | Required | Must match a value in [CATEGORIES.md](CATEGORIES.md) (following the [official taxonomy](https://promptintel.novahunting.ai/taxonomy)) in the format: `category/subcategory`. |
| `severity` | Required | One of: `low`, `medium`, `high`, `critical`. |
| `uuid` | Required | A unique Version 4 UUID. |
| `date` | Required | Initial creation date in `YYYY-MM-DD` format. |
| `hash` | Optional | File hash for integrity verification. |
| `reference` | Optional | External link to research, reports, or examples. |
| `modified` | Optional | Last update date in `YYYY-MM-DD` format. |

> **Note**: Metadata fields are strictly validated. Including unknown or unofficial fields will cause a validation error.

## Detection Sections

1. **`keywords`**: Direct string matching or regular expressions. Best for specific payloads or known malicious strings.
2. **`semantics`**: Intent-based detection using semantic similarity. Requires a threshold (0.0 to 1.0).
3. **`llm`**: Powerful natural language verification. Use this for complex logic that keywords can't capture. Requires a threshold.
4. **`condition`**: The boolean logic that determines if the rule triggers.

## Rule Requirements

- **Naming Convention**: All rules must follow the `PascalCase` format (e.g., `SuspiciousBase64Injection` instead of `suspicious_base64`).
- **Unique Rule Names**: Every rule must have a unique name across the entire repository.
- **File Extensions**: All rule files must use the `.nov` extension. Other extensions like `.yara` or `.rule` are not permitted.
- **Granular Categories**: Always use the most specific subcategory available in [CATEGORIES.md](CATEGORIES.md) (based on the [official taxonomy](https://promptintel.novahunting.ai/taxonomy)).
- **Test Your Rules**: Ensure your conditions are not too broad (preventing false positives) or too narrow (missing obvious variations).

## Rule Testing

Testing is a critical part of the rule development process. Nova rules are tested using YAML files located in the `tests/` directory.

### Test Format

Each rule should have a corresponding test file (e.g., `your_rule_tests.yaml`). The test runner enforces a strict schema for these files to ensure consistency and reliability.

**Mandatory Fields:**
- `rule_file`: **(Top-level)** The relative path to the `.nov` file containing the rule(s).
- `name`: **(Per test)** A descriptive name for the test case.
- `rule_name`: **(Per test)** The exact name of the rule to be tested (as defined in the `.nov` file). Note: This must be specified for every test case.
- `expected_match`: **(Per test)** A boolean (`true` or `false`) indicating if the rule is expected to trigger.
- `prompt` OR `prompts`: **(Per test)** The input string(s) to test.
    - Use `prompt` for a single test string.
    - Use `prompts` for a list of strings (each will be treated as a separate test case).
    - **Note:** You cannot define both `prompt` and `prompts` in the same test case.

```yaml
rule_file: "your_rule.nov"
tests:
  - name: "Test case description (positive)"
    rule_name: "YourRuleName"
    prompts:
      - "A prompt that SHOULD trigger the rule"
      - "Another prompt that SHOULD trigger the rule"
    expected_match: true

  - name: "Test case description (negative)"
    rule_name: "YourRuleName"
    prompt: "A benign prompt that should NOT trigger the rule"
    expected_match: false
```

## Threshold Guidelines

The threshold (0.0–1.0) determines the sensitivity of `semantics` and `llm` matches.

*   **Recall (0.1–0.3)**: More matches, higher risk of false positives. Best for broad patterns.
*   **Precision (0.7–0.9)**: Stricter matching, lower risk of false positives. Best for specific behaviors.
*   **Balanced (0.4-0.6)**: Recommended starting point for most rules.
