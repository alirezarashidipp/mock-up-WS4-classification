# Classification

## Purpose

This small Python demo classifies incident accountability from recorded evidence. It reads `data/input/RAW_INCIDENTS.csv` and writes the original source values plus classification results to `data/output/CLASSIFIED_INCIDENTS.csv`, relative to the project root.

- **HSBC:** recorded causal evidence supports HSBC accountability.
- **SUPPLIER:** recorded causal evidence supports supplier accountability; extract the documented supplier base name and related facts.
- **UNCERTAIN:** insufficient or conflicting evidence prevents attribution. Explain the specific limit. This is a successful unresolved classification.

The model assesses support, counterevidence, confirmations, and explicit corrections across the included incident fields. An affected actor or resolver is not automatically responsible.

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

The root `main.py` is the sole processing entry point. Application modules stay directly under `app/`; the explicit connection check is `test/check_llm_connection.py`.

1. `read_csv`: read the input without changing source values.
2. Use `COLUMNS`, loaded once from [fields/columns.yml](../fields/columns.yml) by `app/read.py` at import.
3. `validate_input`: check all rows, headers, unique nonblank IDs, and configured definitions before provider calls.
4. `load_prompt`: read the selected prompt, currently [classification_v4.yml](../prompts/classification_v4.yml), and replace `$semantic` placeholders using the aliases on `Classification.model_fields`.
5. Open the configured connection through `llm_connection`; for each row, use `prepare_fields`, call `request_classification` for the raw response, then call `validate_output` explicitly.
6. Use `save_row` to format the result and atomically save accumulated successful rows before the next model call. Close the connection resources when the run ends.

`fields/columns.yml` holds only `input` roles, `input_order`, `exclude: []`, and English field `definitions`. Keep source headers and input configuration consistent; restart the command after edits.
`prepare_fields` in `app/read.py` prepares included values as `InputField(name, description, value)`, following `input_order`, then remaining source order. The configured ID and exact `exclude` headers send no name, definition, or value; all source values remain in the output. Unknown exclusions or no remaining incident fields are rejected. Included fields and configured input roles require definitions.
The YAML prompt supplies system instructions; incident JSON is user-message data. Detailed extraction instructions and rating rubrics belong in that prompt.

`PROMPT_VERSION = "v4"` in `main.py` selects `prompts/classification_v4.yml` for both the batch and live check. The batch prints the selected filename before calls.
For a revision, copy v4 to `classification_v5.yml`, edit the new file, switch the constant to `"v5"`, and rerun. Keep old version files. Missing selected files stop before provider calls without fallback.
Versions cover prompt text; column configuration and schema remain current. Output columns and paths do not change when selecting a version.

## Classification response

The output keeps every source column and value, followed by 19 required output fields: six incident-context fields, one citation field, seven classification fields, and five Supplier fields. The table shows output names in response order. `app/schema.py` defines an ordinary `Classification(BaseModel)` class with typed semantic attributes; its literal `Field(alias="llm_...")` values are the single source of output names. Prompt rendering, response validation, and citation formatting derive aliases from `Classification.model_fields`, while alias serialization preserves those names in the CSV. `validate_output` in `app/validation.py` applies classification rules after Pydantic type validation.

| Field | Meaning |
| --- | --- |
| `llm_affected_service` | Recorded affected products, services, or systems; separate multiple values with `; `. |
| `llm_incident_country` | Recorded country of the incident or affected service. |
| `llm_affected_party` | Recorded affected actors or groups; separate multiple values with semicolons. |
| `llm_business_impact` | Recorded consequences and supported quantities. |
| `llm_resolving_party` | Actor that restored service or resolved the problem. |
| `llm_restoration_action` | Actual restoration action or workaround. |
| `llm_citations` | Source-labeled excerpts. |
| `llm_root_cause` | Recorded cause, when known. |
| `llm_source_consistency` | Agreement between distinct material causal accounts. |
| `llm_accountability_rationale` | Two to four concise sentences covering recorded causal evidence, its link to accountability, material counterevidence or limits, and why the selected class fits. |
| `llm_accountability` | HSBC, SUPPLIER, or UNCERTAIN. |
| `llm_attribution_evidence_strength` | Strength of recorded attribution evidence. |
| `llm_accountability_decision_confidence` | Model confidence in its selected accountability decision (HSBC, SUPPLIER, or UNCERTAIN), not a calibrated probability of responsibility. |
| `llm_hsbc_responsible_function` | Accountable HSBC function. |
| `llm_supplier_name` | Documented base supplier name. |
| `llm_supplier_name_rationale` | Source basis for the name or why it is Unknown. |
| `llm_supplier_product_or_service` | Recorded supplier product or service. |
| `llm_supplier_action_or_failure` | Recorded supplier action, defect, or omission. |
| `llm_supplier_additional_info` | Additional supplier facts. |

Each Pydantic field declares an English description and an initial/default value. The provider schema removes defaults and unsupported limits and explicitly requires all 19 response keys, including nullable keys. `validate_output(response)` in `app/validation.py` checks choices, completion, refusal, content, and the exact key set before constructing the Pydantic model. Missing provider keys are rejected rather than filled from defaults. JSON null becomes a blank CSV cell; `Unknown` remains text. Citations accept `[]`; citation excerpt lines join with newline characters without an added stage prefix. Excerpts remain unverified; schema validation does not establish factual accuracy.

## Ratings and conditional fields

- Attribution evidence: UNSUPPORTED, WEAK, MODERATE, STRONG, VERY_STRONG. HSBC/SUPPLIER cannot use UNSUPPORTED; UNCERTAIN cannot use STRONG/VERY_STRONG.
- Confidence: VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH. UNCERTAIN with VERY_HIGH is valid.
- Source consistency: CONSISTENT, INCONSISTENT, or null when comparable material is insufficient.

These are separate text ratings, not summed scores or calibrated probabilities. Numeric ratings are rejected.
`validate_output` uses ordinary explicit checks after Pydantic type validation to reject invalid class/evidence combinations and apply conditional normalization: all five Supplier fields become null for HSBC/UNCERTAIN; for SUPPLIER, missing name/product/action becomes `Unknown`, blank additional information becomes null, and a nullable name rationale stays null.
The HSBC function uses BUSINESS, TECHNOLOGY, MIXED, or UNCERTAIN; it may be null for HSBC and is null for other classes. Missing or ambiguous incident-context facts stay null.
The provider schema stays flat with 19 required keys, nullable where declared. Conditional rules run locally because Structured Outputs does not support `if`/`then`/`else`. See [OpenAI's supported schema rules](https://developers.openai.com/api/docs/guides/structured-outputs#some-type-specific-keywords-are-not-yet-supported).

## Connection and saving

Reuse `app/llm_connection.py` for the existing OpenAI/Azure authentication, project-root `.env`, and shared `request_classification` request. `app/read.py` owns column configuration, CSV reading, input validation, and field preparation. `app/schema.py` owns only `InputField`, `Classification`, and provider-schema conversion. `app/validation.py` owns response validation followed by explicit classification rules; `app/write.py` owns citation formatting and atomic saves through `save_row`. `request_classification` returns the raw response for explicit validation in `main.py`. Requests use strict Structured Outputs, `store=False`, a 60-second SDK timeout, and one SDK retry, with temperature read from `LLM_TEMPERATURE` (default `0.7`, range `0` to `2`) and no explicit token limit. Invalid temperature settings stop before model requests. The configured model or deployment must support `temperature`. Input column configuration preserves the classification rules and schema-defined output names. See [setup](../README.md#setup).
Each run starts the whole input again without resume or status fields; input stays read-only. Before the first successful save, old output is unchanged. The first success replaces it with current-run results; each later success adds a row through atomic replacement. A later failure stops the run and retains those completed rows.

## Explicit live check

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s test -p check_llm_connection.py -v
```

This check sends one visibly synthetic incident and writes no incident CSV. A pass demonstrates one valid provider response, not model accuracy or calibration. Offline checks do not verify provider connectivity.
