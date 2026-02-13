from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class DiscoveredField(BaseModel):
    raw_label: str
    canonical_field: str | None = None
    inferred_type: Literal[
        "identifier",
        "text",
        "date",
        "enum",
        "composite_enum",
        "reference_list",
        "number",
        "boolean",
        "person_or_role",
        "list",
        "unknown"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    mapping_rationale: str = ""
    example_values: list[str] = Field(default_factory=list, max_length=5)
    date_format: str | None = None
    delimiter: str | None = None
    discovered_enum_values: list[str] | None = None
    composite_components: list[str] | None = None
    references_entity: str | None = None
    nullable_observed: bool = False
    occurrence_rate: float = 1.0


class DiscoveredEntity(BaseModel):
    discovered_label: str
    identifier_field: str | None = None
    identifier_pattern: str | None = None
    record_count: int
    fields: list[DiscoveredField]


class DiscoveredRelationship(BaseModel):
    from_entity: str
    from_field: str
    to_entity: str
    to_field: str
    cardinality: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


class SchemaMap(BaseModel):
    document_format: str
    structural_pattern: Literal[
        "vertical_key_value_tables",
        "horizontal_tables",
        "section_based_prose",
        "flat_spreadsheet",
        "mixed",
        "unknown"
    ]
    structural_confidence: float = Field(ge=0.0, le=1.0)
    inferred_document_category: Literal["grc_library", "regulatory", "data_dictionary", "unknown"]
    entities: list[DiscoveredEntity]
    relationships: list[DiscoveredRelationship]
    unmapped_fields: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    total_records_estimated: int
    schema_version: str
    avg_confidence: float
