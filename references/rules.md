# NOVA Rules Reference

## Rule Structure

Nova rules use a custom `.nov` format. This template illustrates a quoted model check used for confirmation. Include only the detection sections the rule needs. Replace metadata placeholders and generate a fresh UUID for each new rule. Preserve its UUID when revising the rule.

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
        promptintel_url = "https://promptintel.novahunting.ai/..."
        modified = "YYYY-MM-DD"

    keywords:
        $keyword1 = "exact string"
        $keyword2 = /regex_pattern/i

    semantics:
        $concept1 = "semantic description of intent" (0.35)

    llm:
        $confirm = "Does the input actively request the behavior? Answer no for benign quotation, documentation, tests, analysis, or warnings." (0.5)

    condition:
        (keywords.$keyword1 or keywords.$keyword2 or semantics.$concept1) and llm.$confirm
}
```

## Model roles and conditions

Role and answer type are separate choices. Below, `llm.$check` can reference any declared quoted LLM check or typed `noul`, `choice`, or `score` question. Typed answers become true/false predicates using their declaration settings; see [Decision model questions](#decision-model-questions).

| Role | Condition | When to use |
| --- | --- | --- |
| Standalone | `llm.$check` | When detecting the behavior requires contextual judgment and a keyword or semantic filter would exclude relevant inputs. |
| Confirmation | `(keywords.$evidence or semantics.$candidate) and llm.$check` | When specific evidence finds candidates, but a model must distinguish active abuse from benign discussion. Validate the filter's attack coverage. |
| Independent fallback | `(keywords.$evidence1 and keywords.$evidence2) or llm.$check` | When explicit evidence can establish a match and the model should also catch the same behavior in missed wording. The model cannot veto evidence-based false positives. |

If the rule needs distinct model judgments, combine their predicates explicitly, such as `llm.$scope and llm.$impact`. Do not add every answer type by default.

Every model question must reject benign quotation, documentation, tests, analysis, and warnings. See [Detection design](#detection-design) for evidence requirements.

## Detection design

- For evidence-only paths, combine two or more checks for distinct facts, such as an action plus a sensitive target. Avoid broad single-keyword or semantic-only detections and duplicated signals. Prefer explicit references over a standalone `any of keywords.*`.
- Use keywords for explicit behavior and semantics for paraphrase coverage. Avoid expensive regex unless necessary. Semantic descriptions should express intent, not just a topic a benign article could discuss.
- Choose the model's role using the table above. Ask a concise question about one mechanism, with explicit benign exclusions; avoid broad questions such as "Is this malicious?". A fallback still covers the same defined behavior.
- Nova evaluates keywords and semantics before model checks; typed decision questions precede quoted LLM checks when both forms occur in a rule. Checks are skipped when other evidence determines the condition. Branch order does not change this stage order; boolean operators define the model's role.

## Local false-positive controls

- Test at least three attacks and three benign look-alikes using similar vocabulary. Exercise each condition path separately, including semantic-only candidates and model-only fallback matches where applicable.
- Require no wrong results in those cases; report skipped, failed, or unresolved checks. Inspect near-threshold semantic and typed answers and add regression cases for weaknesses found. Temperature is not a confidence cutoff.
- Rerun after every edit, including metadata. Local results establish behavior only on the supplied inputs.

## Metadata Requirements

All rules must include the following fields in the `meta` section:

| Field | Requirement | Description |
| :--- | :--- | :--- |
| `description` | Required | High-level explanation of the detection goal. |
| `author` | Required | Credit for the rule creator. |
| `version` | Required | Semantic versioning (e.g., `1.0.0`). |
| `category` | Required | Must match a value in [CATEGORIES.md](CATEGORIES.md) (following the [official taxonomy](https://promptintel.novahunting.ai/taxonomy)) in the format: `category/subcategory`. |
| `severity` | Required | One of: `low`, `medium`, `high`, `critical`. |
| `uuid` | Required | A unique Version 4 UUID, generated once for a new rule and preserved across revisions. |
| `date` | Required | Initial creation date in `YYYY-MM-DD` format. |
| `hash` | Optional | File hash for integrity verification. |
| `reference` | Optional | External link to research, reports, or examples. |
| `promptintel_url` | Optional | Link to the source [PromptIntel](https://promptintel.novahunting.ai) feed item a rule was curated from. |
| `modified` | Optional | Last update date in `YYYY-MM-DD` format. |

> **Note**: Metadata fields are strictly validated. Including unknown or unofficial fields will cause a validation error.

## Decision model questions

The `llm:` section supports quoted questions evaluated by LLMs and `noul`, `choice`, and `score` questions evaluated by decision models. Conditions reference either form as `llm.$name`; quantifiers such as `all of llm` include both. Variable names must be unique across all declarations in the section. Decision models answer the typed questions, and Nova converts their answers into predicates using the declaration settings.

Typed questions retain the separate Decision provider configuration and testing options below. Quoted LLM checks remain fully supported and retain their provider configuration and parenthesized-value behavior; they are not deprecated.

| Primitive | Use for | Required settings | Match rule |
| --- | --- | --- | --- |
| `noul` | One yes/no proposition | `true`, `false`, `threshold` | Probability of yes `>= threshold` |
| `choice` | One category among alternatives | `options`, `match` | Selected option belongs to `match` |
| `score` | A position on a described spectrum | `levels`, `threshold` | Fractional score `>= threshold` |

### Choosing a question type

Ask one focused judgment per question. For distinct factors, combine predicates in `condition:`; questions do not see each other's answers. Similar questions to one model are not independent corroboration.

The examples show only question declarations. Choose their role separately using [Model roles and conditions](#model-roles-and-conditions). Thresholds are illustrative.

### Noul

Ask one question with clear positive polarity. Describe both sides of the boundary, including benign quotation or analysis. Use separate Nouls for properties that can coexist, then combine their predicates in the condition.

```nova
llm:
    $override = noul "Does text actively ask the assistant to disregard governing instructions?" {
        true = "An instruction to disregard governing instructions"
        false = "An ordinary request, quotation, or analysis without a request to execute an override"
        threshold = 0.75
    }
```

Noul is a probability of yes, not a degree of harm. Its threshold is in `[0,1]`. With `0.75`, a valid answer of `0.75` matches and `0.55` does not; a middle value does not automatically become unknown.

### Choice

Make option names and descriptions distinguishable. Choice always selects one category, even when none fits well. When the options may not cover the input, consider a companion Noul that checks whether any category fits, and require its predicate alongside the Choice predicate. A suitable fallback category is another option to validate on labelled inputs. Use separate Nouls when several labels can apply at once.

```nova
llm:
    $operation = choice "Does text request an external transfer or merely discuss one?" {
        options = {
            transfer = "An instruction to send local information to an external recipient"
            discussion = "Quotation or analysis without a transfer request"
            other = "A request unrelated to transferring information externally"
        }
        match = ["transfer"]
        min_confidence = 0.60
    }
```

Nova accepts 2–10 options with nonempty string descriptions. Keys contain letters, digits, or underscores; `match` lists unique declared keys. Confidence describes the concentration of the answer distribution and differs from the winning option's probability.

### Score

Describe concrete situations along one dimension, from low to high. Each level must make sense on its own; avoid bare numbers, vague degrees, or references to neighboring levels. Split different dimensions into separate assessments.

```nova
llm:
    $exposure = score "How much credential exposure would the action requested in text cause?" {
        levels = [
            "No credential exposure",
            "Exposure limited to disposable test credentials",
            "Exposure of credentials for one live account or service",
            "Exposure of credentials for multiple live accounts or services"
        ]
        threshold = 2.0
        min_confidence = 0.60
    }
```

Nova accepts 2–10 levels. Their array positions define a `0`–`N-1` scale; the threshold uses that range. The score is the probability-weighted mean of those positions: probabilities `0.0`, `0.57`, and `0.43` yield `1.43`. Different distributions can yield the same score, so inspect probabilities and confidence when evaluating the rule. Higher confidence alone does not establish correctness.

### Syntax and conditions

- Combine declared predicates with `and`, `or`, `not`, and parentheses, such as `keywords.$transfer and llm.$active`. Quantifiers include `any of llm`, `all of llm`, `2 of llm`, and `any of llm.$risk*`. References and selectors must resolve to declared variables; counts must fit the selection.
- Put thresholds in declarations. Conditions use predicates, not raw answer comparisons, weighted sums, or function calls.
- Choice and Score accept optional `min_confidence` in `[0,1]`; Noul does not. Low or missing required confidence leaves the predicate unknown. If that predicate is needed to determine the outcome, the assessment is incomplete.

## Rule Requirements

- **Naming Convention**: All rules must follow the `PascalCase` format (e.g., `SuspiciousBase64Injection` instead of `suspicious_base64`).
- **Unique Rule Names**: Every rule must have a unique name across the entire repository.
- **File Extensions**: All rule files must use the `.nov` extension. Other extensions like `.yara` or `.rule` are not permitted.

## Rule Testing

### Test Format

Store YAML cases in `tests/` using these required fields:

- `rule_file`: **(Top-level)** The relative path to the `.nov` file containing the rule(s).
- `name`: **(Per test)** A descriptive name for the test case.
- `rule_name`: **(Per test)** The exact name of the rule to be tested (as defined in the `.nov` file).
- `expected_match`: **(Per test)** `true` or `false` for a completed match/nonmatch; `null` for an expected incomplete evaluation.
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

### Decision model tests

The optional per-test `decision_state` supplies caller context, such as `approved_task` and `current_action`; `prompt` remains the action to check.


Enable `--decision-testing` and select a provider/model to evaluate these prompts. Without the flag, tests whose outcomes require Decision evaluation are skipped.

```bash
# Local Ollama model already installed by the user:
python3 scripts/tests/test_rules.py --rules-dir <repo_path> --tests-dir <live_tests> \
  --decision-testing --decision-provider ollama --decision-model laya:latest \
  --decision-host http://127.0.0.1:11434 -v

# Sends inputs and supplied context to OpenRouter:
python3 scripts/tests/test_rules.py --rules-dir <repo_path> --tests-dir <live_tests> \
  --decision-testing --decision-provider openrouter --decision-model typesafe/jev-1.14 \
  --config /tmp/nova-config -v
```

A config file can supply Decision settings and credentials, but live Decision requests still require `--decision-testing`. `--llm-testing` enables existing quoted checks separately. For mixed rules, enable both flags and configure the provider/model for each form. Both use the same YAML prompt tests; no fixed model answers are supplied. Verbose output includes typed answers, scores, confidence, and failure reasons.

## Threshold Guidelines

Semantic thresholds (0.0–1.0) determine the sensitivity of `semantics` matches. Start semantic thresholds around `0.40`–`0.45` unless labelled tests justify a different value. The parenthesized value in a quoted `llm` check is model temperature, not a match threshold. Decision model questions use their declaration settings.

*   **Recall (0.1–0.3)**: More matches, higher risk of false positives. Best for broad patterns.
*   **Precision (0.7–0.9)**: Stricter matching, lower risk of false positives. Best for specific behaviors.
*   **Balanced (0.4-0.6)**: Recommended starting point for most rules.
