from pathlib import Path
from string import Template

import yaml

from app.read import COLUMNS, prepare_fields, read_csv, validate_input
from app.write import save_row
from app.llm_connection import llm_connection, request_classification
from app.schema import Classification
from app.validation import validate_output


ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data/input/RAW_INCIDENTS.csv"
OUTPUT_FILE = ROOT / "data/output/CLASSIFIED_INCIDENTS.csv"
PROMPT_VERSION = "v4"
PROMPT_FILE = ROOT / f"prompts/classification_{PROMPT_VERSION}.yml"


def load_prompt(path):
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    output_names = {name: field.alias for name, field in Classification.model_fields.items()}
    return Template(content["system"]).substitute(output_names)


def main(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    rows = read_csv(input_file)
    validate_input(rows, COLUMNS, input_file, output_file)
    prompt = load_prompt(PROMPT_FILE)
    print(f"Using prompt: {PROMPT_FILE.name}")
    results = []
    with llm_connection() as (client, model):
        for row in rows:
            fields = prepare_fields(row)
            response = request_classification(client, model, fields, prompt)
            result = validate_output(response)
            save_row(output_file, results, row, result)
    print(f"Saved {len(results)} classifications to {output_file}")
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Provider and validation details may contain credentials or source text.
        print(f"Classification stopped: {type(error).__name__}. Last successful save is preserved.")
        raise SystemExit(1) from None
