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
2. Use `COLUMNS`, loaded once from [fields/columns.yml](../fields/columns.yml) when `app/models.py` builds the response schema.
3. `validate_input`: check all rows, headers, unique nonblank IDs, and configured definitions before provider calls.
4. `load_prompt`: read the selected prompt, currently [classification_v1.yml](../prompts/classification_v1.yml), and replace `$semantic` placeholders using the configured output names.
5. For each row, prepare included fields, call the model, and validate the result with Pydantic.
6. Save accumulated successful rows atomically before the next model call.

`fields/columns.yml` holds `input` roles, `input_order`, `exclude: []`, English field `definitions`, and 20 unique `output` names starting with `llm_`. Change names without changing fixed roles or Python types; restart the command after edits.
`prepare_fields` sends included values as `InputField(name, description, value)`, following `input_order`, then remaining source order. The configured ID and exact `exclude` headers send no name, definition, or value; all source values remain in the output. Unknown exclusions or no remaining incident fields are rejected. Included fields and configured input roles require definitions.
The YAML prompt supplies system instructions; incident JSON is user-message data. Detailed extraction instructions and rating rubrics belong in that prompt.

`PROMPT_VERSION = "v1"` in `app/classification.py` selects `prompts/classification_v1.yml` for both the batch and live check. The batch prints the selected filename before calls.
For a revision, copy v1 to `classification_v2.yml`, edit the new file, switch the constant to `"v2"`, and rerun. Keep old version files. Missing selected files stop before provider calls without fallback.
Versions cover prompt text; column configuration and schema remain current. Output columns and paths do not change when selecting a version.

## Classification response

The output keeps every source column and value, followed by 20 required configured fields: six incident-context fields, two evidence references, seven classification fields, and five Supplier fields. The table shows current default names in response order. `app/models.py` defines types and local model validation; `columns.yml` supplies names.

| Field | Meaning |
| --- | --- |
| `llm_affected_service` | Recorded affected product, service, or system. |
| `llm_incident_country` | Recorded country of the incident or affected service. |
| `llm_affected_party` | Recorded affected actor or group. |
| `llm_business_impact` | Recorded consequences and supported quantities. |
| `llm_resolving_party` | Actor that restored service or resolved the problem. |
| `llm_restoration_action` | Actual restoration action or workaround. |
| `llm_evidence_columns` | Ordered list of source column names. |
| `llm_citations` | Source-labeled excerpts. |
| `llm_root_cause` | Recorded cause, when known. |
| `llm_source_consistency` | Agreement between distinct material causal accounts. |
| `llm_accountability_rationale` | Concise explanation of support, counterevidence, and gaps. |
| `llm_accountability` | HSBC, SUPPLIER, or UNCERTAIN. |
| `llm_attribution_evidence_strength` | Strength of recorded attribution evidence. |
| `llm_accountability_confidence` | Model confidence in its selected class. |
| `llm_hsbc_responsible_function` | Accountable HSBC function. |
| `llm_supplier_name` | Documented base supplier name. |
| `llm_supplier_name_rationale` | Source basis for the name or why it is Unknown. |
| `llm_supplier_product_or_service` | Recorded supplier product or service. |
| `llm_supplier_action_or_failure` | Recorded supplier action, defect, or omission. |
| `llm_supplier_additional_info` | Additional supplier facts. |

All keys are required, including nullable keys. JSON null becomes a blank CSV cell; `Unknown` remains text. Evidence and citations accept `[]`: evidence names join with comma and space; citation lines receive `Classification:` prefixes. Excerpts remain unverified; schema validation does not establish factual accuracy.

## Ratings and conditional fields

- Attribution evidence: UNSUPPORTED, WEAK, MODERATE, STRONG, VERY_STRONG. HSBC/SUPPLIER cannot use UNSUPPORTED; UNCERTAIN cannot use STRONG/VERY_STRONG.
- Confidence: VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH. UNCERTAIN with VERY_HIGH is valid.
- Source consistency: CONSISTENT, INCONSISTENT, or null when comparable material is insufficient.

These are separate text ratings, not summed scores or calibrated probabilities. Numeric ratings are rejected.
The local Pydantic model validator rejects invalid class/evidence combinations and applies conditional normalization: all five Supplier fields become null for HSBC/UNCERTAIN; for SUPPLIER, missing name/product/action becomes `Unknown`, blank additional information becomes null, and a nullable name rationale stays null.
The HSBC function uses BUSINESS, TECHNOLOGY, MIXED, or UNCERTAIN; it may be null for HSBC and is null for other classes. Missing or ambiguous incident-context facts stay null.
The provider schema stays flat with 20 required keys, nullable where declared. Conditional rules run locally because Structured Outputs does not support `if`/`then`/`else`. See [OpenAI's supported schema rules](https://developers.openai.com/api/docs/guides/structured-outputs#some-type-specific-keywords-are-not-yet-supported).

## Connection and saving

Reuse `app/llm_connection.py` for OpenAI/Azure and the project-root `.env`. Requests use strict Structured Outputs, `store=False`, a 60-second SDK timeout, and one SDK retry, without temperature or token controls. Column configuration changes names, not classification rules. See [setup](../README.md#setup).
Each run starts the whole input again without resume or status fields; input stays read-only. Before the first successful save, old output is unchanged. The first success replaces it with current-run results; each later success adds a row through atomic replacement. A later failure stops the run and retains those completed rows.

## Explicit live check

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s test -p check_llm_connection.py -v
```

This check sends one visibly synthetic incident and writes no incident CSV. A pass demonstrates one valid provider response, not model accuracy or calibration. Offline checks do not verify provider connectivity.
