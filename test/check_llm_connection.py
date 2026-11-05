"""Live connection check. Run explicitly; ordinary test discovery skips this file."""

import unittest

from main import PROMPT_FILE, load_prompt
from app.llm_connection import llm_connection, request_classification
from app.read import COLUMNS, prepare_fields
from app.validation import validate_output


class LLMConnectionTest(unittest.TestCase):
    def test_llm_responds(self):
        input_columns = COLUMNS["input"]
        row = {
            input_columns["id"]: "SYNTHETIC-CONNECTION-CHECK",
            input_columns["description"]: "Synthetic connection check: an internal payment service was temporarily unavailable.",
            input_columns["root_cause"]: "Synthetic confirmed finding: an HSBC engineer applied an incorrect internal routing configuration. Reverting that change restored the service. No supplier action caused this example incident.",
        }
        try:
            fields = prepare_fields(row, COLUMNS)
            if not fields:
                raise ValueError("The connection check needs at least one included synthetic incident field.")
            prompt = load_prompt(PROMPT_FILE)
            with llm_connection() as (client, model):
                response = request_classification(client, model, fields, prompt)
                result = validate_output(response)
        except Exception as error:
            # Provider and validation errors may contain credentials or input values.
            raise AssertionError(
                f"LLM connection check failed: {type(error).__name__}. "
                "Check .env, connectivity, prompt files, and structured-output support."
            ) from None

        self.assertIsNotNone(
            result,
            "The model response was empty, refused, incomplete, or failed classification validation.",
        )
        accountability = result.accountability
        self.assertIn(accountability, ("HSBC", "SUPPLIER", "UNCERTAIN"))
        print("Connection check passed: the synthetic request returned a valid structured classification. No CSV files were read or written.")


if __name__ == "__main__":
    unittest.main()
