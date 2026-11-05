"""Read input configuration and CSV rows, then prepare included fields."""

import csv
from pathlib import Path

import yaml

from app.schema import InputField


COLUMNS_FILE = Path(__file__).resolve().parents[1] / "fields/columns.yml"


def load_columns(path):
    text = path.read_text(encoding="utf-8")
    columns = yaml.safe_load(text)
    excluded = columns["exclude"]
    if not isinstance(excluded, list):
        raise ValueError("Exclude must be a list of exact input column names.")
    for name in excluded:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Excluded column names must be nonblank strings.")

    order = columns["input_order"]
    if len(order) != len(set(order)):
        raise ValueError("Input order cannot contain repeated columns.")
    for name in columns["input"].values():
        if name not in columns["definitions"] or name.startswith("llm_"):
            raise ValueError("Input roles require defined source columns.")
    if len(set(columns["input"].values())) != len(columns["input"]):
        raise ValueError("Input roles must use distinct columns.")
    return columns


COLUMNS = load_columns(COLUMNS_FILE)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError("CSV headers must be nonblank and unique.")
        if len(columns) != len(set(columns)):
            raise ValueError("CSV headers must be nonblank and unique.")
        for name in columns:
            if not name.strip():
                raise ValueError("CSV headers must be nonblank and unique.")
        rows = list(reader)
    for row in rows:
        if None in row or None in row.values():
            raise ValueError("CSV rows must have the same number of cells as the headers.")
    return rows


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


def prepare_fields(row: dict[str, str], columns=COLUMNS) -> list[dict[str, str]]:
    id_column = columns["input"]["id"]
    definitions = columns["definitions"]
    excluded = columns["exclude"]
    names = []
    for name in columns["input_order"]:
        if name in row and name != id_column and name not in excluded:
            names.append(name)
    # Keep additional source columns in their original order.
    for name in row:
        if name != id_column and name not in excluded and name not in names:
            names.append(name)

    fields = []
    for name in names:
        field = InputField(name=name, description=definitions[name], value=row[name])
        fields.append(field.model_dump())
    return fields
