"""Column names from YAML, with explicit input and response types."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator


COLUMNS_FILE = Path(__file__).resolve().parents[1] / "fields/columns.yml"


def load_columns(path):
    text = path.read_text(encoding="utf-8")
    columns = yaml.safe_load(text)
    names = list(columns["output"].values())
    if len(names) != 20:
        raise ValueError("Configure all 20 output columns.")
    for name in names:
        if not isinstance(name, str) or not name.startswith("llm_") or not name.isidentifier():
            raise ValueError("Output names must be identifiers starting with llm_.")
    if len(names) != len(set(names)):
        raise ValueError("Output column names must be unique.")

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
OUTPUT_COLUMNS = COLUMNS["output"]
SUPPLIER_FIELDS = (
    OUTPUT_COLUMNS["supplier_name"],
    OUTPUT_COLUMNS["supplier_name_rationale"],
    OUTPUT_COLUMNS["supplier_product_or_service"],
    OUTPUT_COLUMNS["supplier_action_or_failure"],
    OUTPUT_COLUMNS["supplier_additional_info"],
)


class InputField(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    value: str


@model_validator(mode="after")
def apply_classification_rules(result):
    """Apply cross-field rules locally; the provider schema defines field types."""
    accountability = getattr(result, OUTPUT_COLUMNS["accountability"])
    strength = getattr(result, OUTPUT_COLUMNS["attribution_evidence_strength"])
    if accountability == "UNCERTAIN" and strength in ("STRONG", "VERY_STRONG"):
        raise ValueError("UNCERTAIN cannot have STRONG or VERY_STRONG attribution evidence.")
    if accountability in ("HSBC", "SUPPLIER") and strength == "UNSUPPORTED":
        raise ValueError("HSBC and SUPPLIER require supported attribution evidence.")

    if accountability != "HSBC":
        setattr(result, OUTPUT_COLUMNS["hsbc_responsible_function"], None)
    if accountability != "SUPPLIER":
        for name in SUPPLIER_FIELDS:
            setattr(result, name, None)
        return result

    for role in ("supplier_name", "supplier_product_or_service", "supplier_action_or_failure"):
        name = OUTPUT_COLUMNS[role]
        value = getattr(result, name)
        if not value or not value.strip():
            setattr(result, name, "Unknown")
    additional_info = OUTPUT_COLUMNS["supplier_additional_info"]
    value = getattr(result, additional_info)
    if not value or not value.strip():
        setattr(result, additional_info, None)
    return result


Classification = create_model(
    "Classification",
    __config__=ConfigDict(extra="forbid"),
    __validators__={"apply_classification_rules": apply_classification_rules},
    **{
        OUTPUT_COLUMNS["affected_service"]: (str | None, ...),
        OUTPUT_COLUMNS["incident_country"]: (str | None, ...),
        OUTPUT_COLUMNS["affected_party"]: (str | None, ...),
        OUTPUT_COLUMNS["business_impact"]: (str | None, ...),
        OUTPUT_COLUMNS["resolving_party"]: (str | None, ...),
        OUTPUT_COLUMNS["restoration_action"]: (str | None, ...),
        OUTPUT_COLUMNS["evidence_columns"]: (list[str], ...),
        OUTPUT_COLUMNS["citations"]: (list[str], ...),
        OUTPUT_COLUMNS["root_cause"]: (str | None, Field(min_length=1)),
        OUTPUT_COLUMNS["source_consistency"]: (Literal["CONSISTENT", "INCONSISTENT"] | None, ...),
        OUTPUT_COLUMNS["accountability_rationale"]: (str, Field(min_length=1)),
        OUTPUT_COLUMNS["accountability"]: (Literal["HSBC", "SUPPLIER", "UNCERTAIN"], ...),
        OUTPUT_COLUMNS["attribution_evidence_strength"]: (Literal["UNSUPPORTED", "WEAK", "MODERATE", "STRONG", "VERY_STRONG"], ...),
        OUTPUT_COLUMNS["accountability_confidence"]: (Literal["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"], ...),
        OUTPUT_COLUMNS["hsbc_responsible_function"]: (Literal["BUSINESS", "TECHNOLOGY", "MIXED", "UNCERTAIN"] | None, ...),
        OUTPUT_COLUMNS["supplier_name"]: (str | None, ...),
        OUTPUT_COLUMNS["supplier_name_rationale"]: (str | None, ...),
        OUTPUT_COLUMNS["supplier_product_or_service"]: (str | None, ...),
        OUTPUT_COLUMNS["supplier_action_or_failure"]: (str | None, ...),
        OUTPUT_COLUMNS["supplier_additional_info"]: (str | None, ...),
    },
)


def format_citations(citations, stage):
    """Label each excerpt line within the classification citation cell."""
    lines = []
    for citation in citations:
        for line in citation.splitlines():
            lines.append(f"{stage}: {line}")
    return "\n".join(lines)


def remove_schema_limits(value):
    # Azure accepts the structure; Pydantic still enforces every limit locally.
    if isinstance(value, dict):
        for keyword in ("minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"):
            value.pop(keyword, None)
        for child in value.values():
            remove_schema_limits(child)
    elif isinstance(value, list):
        for child in value:
            remove_schema_limits(child)
