"""Validate and normalize the response after the LLM returns."""

import json

from app.schema import Classification


def validate_output(response):
    if not response.choices:
        raise ValueError("The model returned no classification.")
    choice = response.choices[0]
    if choice.finish_reason != "stop":
        raise ValueError("The model returned an incomplete classification.")
    message = choice.message
    if message.refusal or not message.content:
        raise ValueError("The model refused or returned an empty classification.")

    # Require the full response before Pydantic can apply defaults.
    values = json.loads(message.content)
    expected = {field.alias for field in Classification.model_fields.values()}
    if not isinstance(values, dict) or set(values) != expected:
        raise ValueError("The model must return exactly the 19 output fields.")
    result = Classification.model_validate(values)

    # Reject invalid attribution, then clear fields that do not apply.
    if result.accountability == "UNCERTAIN" and result.attribution_evidence_strength in ("STRONG", "VERY_STRONG"):
        raise ValueError("UNCERTAIN cannot have STRONG or VERY_STRONG attribution evidence.")
    if result.accountability in ("HSBC", "SUPPLIER") and result.attribution_evidence_strength == "UNSUPPORTED":
        raise ValueError("HSBC and SUPPLIER require supported attribution evidence.")

    if result.accountability != "HSBC":
        result.hsbc_responsible_function = None
    if result.accountability != "SUPPLIER":
        result.supplier_name = None
        result.supplier_name_rationale = None
        result.supplier_product_or_service = None
        result.supplier_action_or_failure = None
        result.supplier_additional_info = None
        return result

    if not result.supplier_name or not result.supplier_name.strip():
        result.supplier_name = "Unknown"
    if not result.supplier_product_or_service or not result.supplier_product_or_service.strip():
        result.supplier_product_or_service = "Unknown"
    if not result.supplier_action_or_failure or not result.supplier_action_or_failure.strip():
        result.supplier_action_or_failure = "Unknown"
    if not result.supplier_additional_info or not result.supplier_additional_info.strip():
        result.supplier_additional_info = None
    return result
