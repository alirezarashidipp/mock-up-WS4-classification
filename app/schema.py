"""Pydantic input/output definitions and provider response schema."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InputField(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, description="Exact included source column name.")
    description: str = Field(min_length=1, description="Column definition, not incident evidence.")
    value: str = Field(default="", description="Unchanged source value.")


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    affected_service: str | None = Field(
        default=None,
        alias="llm_affected_service",
        description="Recorded affected services; separate multiple services with semicolons.",
    )
    incident_country: str | None = Field(
        default=None,
        alias="llm_incident_country",
        description="Recorded incident countries in English; separate multiple countries with semicolons.",
    )
    affected_party: str | None = Field(
        default=None,
        alias="llm_affected_party",
        description="Recorded affected actors or groups; separate multiple actors with semicolons.",
    )
    business_impact: str | None = Field(
        default=None,
        alias="llm_business_impact",
        description="Recorded business consequences and supported quantities.",
    )
    resolving_party: str | None = Field(
        default=None,
        alias="llm_resolving_party",
        description="Recorded actors that restored service; separate multiple actors with semicolons.",
    )
    restoration_action: str | None = Field(
        default=None,
        alias="llm_restoration_action",
        description="Actual recorded restoration action or workaround.",
    )
    citations: list[str] = Field(
        default_factory=list,
        alias="llm_citations",
        description="Source-labeled excerpts supporting attribution or counterevidence.",
    )
    root_cause: str | None = Field(
        default=None,
        min_length=1,
        alias="llm_root_cause",
        description="Recorded cause in one sentence, or null when unknown.",
    )
    source_consistency: Literal["CONSISTENT", "INCONSISTENT"] | None = Field(
        default=None,
        alias="llm_source_consistency",
        description="Agreement between distinct material causal accounts; null if not comparable.",
    )
    accountability_rationale: str = Field(
        default="",
        min_length=1,
        alias="llm_accountability_rationale",
        description="Concise attribution support, counterevidence, and specific gaps.",
    )
    accountability: Literal["HSBC", "SUPPLIER", "UNCERTAIN"] = Field(
        default="UNCERTAIN",
        alias="llm_accountability",
        description="Recorded causal accountability, including unresolved attribution.",
    )
    attribution_evidence_strength: Literal["UNSUPPORTED", "WEAK", "MODERATE", "STRONG", "VERY_STRONG"] = Field(
        default="UNSUPPORTED",
        alias="llm_attribution_evidence_strength",
        description="Strength of recorded evidence for assigning accountability.",
    )
    accountability_confidence: Literal["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"] = Field(
        default="VERY_LOW",
        alias="llm_accountability_decision_confidence",
        description="Model confidence in its chosen accountability decision, not a calibrated probability.",
    )
    hsbc_responsible_function: Literal["BUSINESS", "TECHNOLOGY", "MIXED", "UNCERTAIN"] | None = Field(
        default=None,
        alias="llm_hsbc_responsible_function",
        description="Accountable HSBC function; null for other classes.",
    )
    supplier_name: str | None = Field(
        default=None,
        alias="llm_supplier_name",
        description="Documented accountable supplier base name; Unknown if unnamed; null for other classes.",
    )
    supplier_name_rationale: str | None = Field(
        default=None,
        alias="llm_supplier_name_rationale",
        description="Source basis for the supplier name or the specific naming gap.",
    )
    supplier_product_or_service: str | None = Field(
        default=None,
        alias="llm_supplier_product_or_service",
        description="Recorded supplier product or service; Unknown if absent for SUPPLIER.",
    )
    supplier_action_or_failure: str | None = Field(
        default=None,
        alias="llm_supplier_action_or_failure",
        description="Recorded supplier action, defect, or omission; Unknown if absent for SUPPLIER.",
    )
    supplier_additional_info: str | None = Field(
        default=None,
        alias="llm_supplier_additional_info",
        description="Additional recorded supplier facts; null when absent or not SUPPLIER.",
    )


def response_schema():
    schema = Classification.model_json_schema()
    schema["required"] = list(schema["properties"])
    remove_schema_limits(schema)
    return schema


def remove_schema_limits(value):
    # Keep provider schema compatible; validate complete responses locally.
    if isinstance(value, dict):
        for keyword in ("default", "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"):
            value.pop(keyword, None)
        for child in value.values():
            remove_schema_limits(child)
    elif isinstance(value, list):
        for child in value:
            remove_schema_limits(child)
