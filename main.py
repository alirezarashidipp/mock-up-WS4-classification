from pathlib import Path

from app.csv_files import read_csv
from app.classification import PROMPT_FILE, classify_rows, load_prompt, validate_input
from app.models import COLUMNS


ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data/input/RAW_INCIDENTS.csv"
OUTPUT_FILE = ROOT / "data/output/CLASSIFIED_INCIDENTS.csv"


def main(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    columns = COLUMNS
    rows = read_csv(input_file)
    validate_input(rows, columns, input_file, output_file)
    prompt = load_prompt(PROMPT_FILE)
    print(f"Using prompt: {PROMPT_FILE.name}")
    results = classify_rows(rows, columns, prompt, output_file)
    print(f"Saved {len(results)} classifications to {output_file}")
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Provider and validation details may contain credentials or source text.
        print(f"Classification stopped: {type(error).__name__}. Last successful save is preserved.")
        raise SystemExit(1) from None
