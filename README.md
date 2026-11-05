# HSBC Incident Classification Demo

A small Python 3.11 demo that reads incident records, uses one selected prompt version with OpenAI or Azure, and writes the original source values plus 20 output fields (`llm_` names by default).

```text
data/input/RAW_INCIDENTS.csv
    + fields/columns.yml
    + prompts/classification_v1.yml
    -> data/output/CLASSIFIED_INCIDENTS.csv
```

The output class is **HSBC**, **SUPPLIER**, or **UNCERTAIN**. UNCERTAIN is a successful unresolved attribution. Results include recorded incident context, concise rationales, supplier facts when applicable, evidence references, and three separate text ratings. See the [classification contract](docs/llm.md) for the exact 20 fields.

## Setup

Run from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create your local `.env` using [.env.example](.env.example). Keep credentials, all CSV files, and local input/output data out of Git.

Choose `LLM_PROVIDER=openai` or `azure`:

- OpenAI: set `OPENAI_API_KEY` and `OPENAI_MODEL` (default `gpt-4.1-mini`).
- Azure: set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_OPENAI_TOKEN_SCOPE`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, and `AZURE_OPENAI_DEPLOYMENT`. The last value is your deployment name. Use your organization's approved scope and API version.
- Corporate proxy settings are optional. Restart the command after changing settings.

The connection is `app/llm_connection.py` and loads the project-root `.env`. Requests use strict Structured Outputs, a 60-second SDK timeout, and one SDK retry, without temperature or token-limit controls.

## Input schema and field descriptions

Place the source at **data/input/RAW_INCIDENTS.csv**, relative to the project root. The required filename is **RAW_INCIDENTS.csv**. Use comma-separated UTF-8 CSV; a UTF-8 BOM is accepted. Keep identifiers as text, including leading zeros, and use normal CSV quoting for commas, quotes, and line breaks.

The repository includes `data/input/` and `data/output/` with empty `.gitkeep` placeholders. Local data files and all CSVs stay excluded from Git.

Configure column names in [fields/columns.yml](fields/columns.yml):

| Section | Contents |
| --- | --- |
| `input` | Fixed roles `id`, `description`, and `root_cause`; defaults are `INCIDENT_ID`, `INCIDENT_DESCRIPTION`, and `ROOT_CAUSE_NOTES`. Each configured role name needs a definition. |
| `input_order` | Source columns in the preferred request order; other columns follow in source order. |
| `exclude` | Exact source headers to omit from model input; default `[]`. The ID is always omitted. |
| `definitions` | Exact source header -> nonblank English description for configured input roles and included incident columns. |
| `output` | The 20 fixed semantic roles -> unique output names, such as `accountability: llm_accountability`. Names must be Python identifiers starting with `llm_`. |

The CSV needs nonblank unique headers, complete rows, a nonblank unique configured ID, and at least one included incident-data column. Included fields need definitions; excluded fields do not, unless they are configured input roles. Reserve the `llm_` prefix for output names. All input is validated before provider calls. Supplied headers, identifiers, and values are preserved without automatic renaming or cleaning.

For example, to keep this exact source column in the output while withholding its name, definition, and value from the model:

```yaml
exclude:
  - ADDITIONAL_COMMENTS
```

Use only headers present in your CSV; unknown exclusion names are rejected to catch typos. Excluding all incident-data columns is rejected. The configured ID always stays local, even with `exclude: []`.

Column names may change while the 20 semantic roles, their meanings, and their Python types remain fixed. Keep CSV headers and configuration consistent. `app/models.py` loads the configuration once when building the Pydantic schema; start a new command after edits.

**Synthetic example — fictional records, not real incidents or live model results:**

```csv
INCIDENT_ID,INCIDENT_SHORT_DESCRIPTION,INCIDENT_DESCRIPTION,IT_INCIDENT_CAUSE_DETAILS
SYNTHETIC-001,Synthetic internal gateway issue,An HSBC operator applied an incorrect gateway setting.,Internal configuration was recorded as the cause.
SYNTHETIC-002,Synthetic supplier gateway issue,Atlas Cloud deployed a gateway change that interrupted service.,The supplier confirmed its deployment caused the interruption.
SYNTHETIC-003,Synthetic unresolved interruption,A service interruption was reported but the responsible party was not established.,
```

The selected prompt is [prompts/classification_v1.yml](prompts/classification_v1.yml). It contains classification instructions and rating rubrics; `load_prompt` resolves its `$semantic` placeholders using the configured output names. [app/models.py](app/models.py) keeps the response types, conditional normalization, and class/evidence checks in Python. The provider schema remains a flat object with 20 required keys; cross-field rules run in local Pydantic validation.

## Prompt versions

`PROMPT_VERSION = "v1"` in `app/classification.py` selects `prompts/classification_v1.yml`. Both the batch and live check use that selection. The batch prints the selected filename before model calls.

To revise the prompt, copy `classification_v1.yml` to `classification_v2.yml`, edit the new file, change the single `PROMPT_VERSION` constant to `"v2"`, and rerun. Keep the old version file. A missing selected file stops before provider calls; there is no automatic latest-version selection or fallback.

Versions cover prompt text. Column configuration and schema still use their current definitions.

## Run

```powershell
.\.venv\Scripts\python.exe main.py
```

The root **main.py** is the sole processing entry point. It validates the complete input, makes one classification request per row, and atomically saves accumulated current-run results to **data/output/CLASSIFIED_INCIDENTS.csv** after each successful row, before the next model call. The output directory is created if needed.

A refused, incomplete, invalid, or failed response stops the run with a safe exception type. Before the first successful save, previous output is unchanged. The first success replaces it; later failures retain completed rows from the current run. Each new run starts the entire input again, without reading previous output or resuming. The source CSV is read-only.

Output columns contain every original input column first, then the [20 configured output fields](docs/llm.md#classification-response). JSON nulls become blank cells. The evidence and citations columns (default `llm_evidence_columns` and `llm_citations`) store ordered source names and unverified excerpts with `Classification:` line prefixes. Attribution evidence, source consistency, and self-reported confidence are separate text ratings, not summed scores or calibrated probabilities.

## Files

```text
main.py                           Sole processing entry point
app/classification.py              Model request and response functions
app/prepare_fields.py              Configured input order and descriptions
app/llm_connection.py              Existing OpenAI/Azure connection
app/models.py                     Column loading, Pydantic types and schema/citation helpers
app/csv_files.py                  CSV reading and atomic writing
fields/columns.yml                Input roles, order, exclusions, definitions and output names
prompts/classification_v1.yml     Selected prompt; keep earlier versions when revising
data/input/RAW_INCIDENTS.csv      Required local source CSV; excluded from Git
data/output/CLASSIFIED_INCIDENTS.csv  Generated CSV; excluded from Git
test/check_llm_connection.py      Explicit live connection check
.env.example                     Provider configuration template
```

## Checks

To check the connection with a real request using your configured provider:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s test -p check_llm_connection.py -v
```

The live check sends one visibly synthetic incident and writes no incident CSV. A pass demonstrates one valid classification response, not model accuracy or calibration.

Read the [project purpose and classification contract](docs/llm.md) and [project instructions](AGENTS.md) for the business rules and implementation constraints.
