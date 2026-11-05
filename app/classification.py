import json
from pathlib import Path
from string import Template

import yaml
from openai import OpenAI

from app.csv_files import write_csv
from app.models import OUTPUT_COLUMNS, Classification, format_citations, remove_schema_limits
from app.llm_connection import llm_connection
from app.prepare_fields import prepare_fields


ROOT = Path(__file__).resolve().parents[1]
PROMPT_VERSION = "v1"
PROMPT_FILE = ROOT / f"prompts/classification_{PROMPT_VERSION}.yml"


def load_prompt(path):
    text = path.read_text(encoding="utf-8")
    content = yaml.safe_load(text)
    template = Template(content["system"])
    return template.substitute(OUTPUT_COLUMNS)


def validate_input(rows, columns, input_file, output_file):
    if input_file.resolve() == output_file.resolve():
        raise ValueError("Input and output must be different files.")
    if not rows:
        raise ValueError("The input CSV must contain incident rows.")

    id_column = columns["input"]["id"]
    definitions = columns["definitions"]
    excluded = columns["exclude"]
    source_columns = list(rows[0])
    if id_column not in source_columns or len(source_columns) < 2:
        raise ValueError(f"Input requires {id_column} and at least one incident field.")
    if not isinstance(definitions, dict):
        raise ValueError("Field definitions must map column names to descriptions.")
    for name in excluded:
        if name not in source_columns:
            raise ValueError("Every excluded column must exactly match an input CSV header.")
    included = []
    for name in source_columns:
        if name.startswith("llm_"):
            raise ValueError("Input columns cannot use the llm_ output prefix.")
        if name == id_column or name in excluded:
            continue
        included.append(name)
        description = definitions.get(name)
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Every incident field requires a nonblank text definition.")
    if not included:
        raise ValueError("At least one incident field must remain available to the model.")

    identifiers = set()
    for row in rows:
        incident_id = row[id_column]
        if not incident_id.strip() or incident_id in identifiers:
            raise ValueError(f"{id_column} values must be nonblank and unique.")
        identifiers.add(incident_id)


def classify_rows(rows, columns, prompt, output_file):
    results = []
    with llm_connection() as (client, model):
        for row in rows:
            fields = prepare_fields(row, columns)
            result = classify_row(client, model, fields, prompt)
            if result is None:
                raise ValueError("The model returned an invalid or incomplete classification.")

            output_row = dict(row)
            values = classification_values(result)
            output_row.update(values)
            results.append(output_row)
            write_csv(output_file, results)
    return results


def classification_values(result: Classification) -> dict:
    values = result.model_dump()
    evidence_column = OUTPUT_COLUMNS["evidence_columns"]
    citation_column = OUTPUT_COLUMNS["citations"]
    values[evidence_column] = ", ".join(values[evidence_column])
    values[citation_column] = format_citations(values[citation_column], "Classification")
    return values


def classification_schema() -> dict:
    schema = Classification.model_json_schema()
    remove_schema_limits(schema)
    return schema

def classify_row(client: OpenAI, model: str, fields: list[dict], prompt: str) -> Classification | None:
    payload = json.dumps(fields, ensure_ascii=False)
    schema = classification_schema()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": payload},
    ]
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "Classification", "strict": True, "schema": schema},
    }
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        store=False,
    )
    return parse_response(response)


def parse_response(response) -> Classification | None:
    if not response.choices:
        return None
    choice = response.choices[0]
    if choice.finish_reason != "stop":
        return None
    message = choice.message
    if message.refusal or not message.content:
        return None
    return Classification.model_validate_json(message.content)
