from __future__ import annotations

import pytest

from agent1.models.schema_map import (
    DiscoveredField,
    DiscoveredEntity,
    SchemaMap,
)
from agent1.nodes.schema_discovery import (
    compute_schema_hash,
    compute_avg_confidence,
)
from agent1.nodes.confidence_gate import check_confidence
from agent1.models.state import Phase1State
from agent1.cache.schema_cache import cache_schema, get_cached_schema


def test_compute_avg_confidence() -> None:
    """Test confidence computation."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
            DiscoveredField(raw_label="Description", inferred_type="text", confidence=0.85),
            DiscoveredField(raw_label="Owner", inferred_type="person_or_role", confidence=0.70),
        ],
    )
    schema_map = SchemaMap(
        document_format="test",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="test",
        avg_confidence=0.0,
    )
    avg = compute_avg_confidence(schema_map)
    assert abs(avg - 0.833) < 0.01


def test_schema_hash_determinism() -> None:
    """Test schema hash is deterministic."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    schema_map = SchemaMap(
        document_format="test",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="",
        avg_confidence=0.0,
    )
    hash1 = compute_schema_hash(schema_map)
    hash2 = compute_schema_hash(schema_map)
    assert hash1 == hash2


def test_confidence_gate_accept() -> None:
    """Test gate accepts high confidence."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    schema_map = SchemaMap(
        document_format="grc_export",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="test",
        avg_confidence=0.92,
    )
    state: Phase1State = {
        "schema_map": schema_map,
        "chunks": [],
        "file_path": "test.docx",
    }
    result = check_confidence(state)
    assert result == "accept"


def test_confidence_gate_review() -> None:
    """Test gate routes to review for medium confidence."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.65),
        ],
    )
    schema_map = SchemaMap(
        document_format="grc_export",
        structural_pattern="mixed",
        structural_confidence=0.7,
        inferred_document_category="grc_library",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="test",
        avg_confidence=0.65,
    )
    state: Phase1State = {
        "schema_map": schema_map,
        "chunks": [],
        "file_path": "test.docx",
    }
    result = check_confidence(state)
    assert result == "human_review"


def test_confidence_gate_reject() -> None:
    """Test gate rejects low confidence."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="unknown", confidence=0.30),
        ],
    )
    schema_map = SchemaMap(
        document_format="grc_export",
        structural_pattern="unknown",
        structural_confidence=0.3,
        inferred_document_category="unknown",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="test",
        avg_confidence=0.30,
    )
    state: Phase1State = {
        "schema_map": schema_map,
        "chunks": [],
        "file_path": "test.docx",
    }
    result = check_confidence(state)
    assert result == "reject"


def test_schema_caching() -> None:
    """Test schema caching."""
    entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    schema_map = SchemaMap(
        document_format="test_tool_unique",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity],
        relationships=[],
        total_records_estimated=5,
        schema_version="test",
        avg_confidence=0.95,
    )
    cache_schema("test_tool_unique", schema_map)
    cached = get_cached_schema("test_tool_unique")
    assert cached is not None
    assert cached.document_format == "test_tool_unique"
    assert len(cached.entities) == 1


def test_discovered_field_validation() -> None:
    """Test DiscoveredField validation."""
    field = DiscoveredField(
        raw_label="Policy ID",
        inferred_type="identifier",
        confidence=0.95,
        example_values=["P-001", "P-002"],
    )
    assert field.raw_label == "Policy ID"
    assert field.confidence == 0.95
    assert len(field.example_values) == 2


def test_discovered_entity_with_multiple_fields() -> None:
    """Test DiscoveredEntity with multiple fields."""
    entity = DiscoveredEntity(
        discovered_label="Policy",
        identifier_field="Policy ID",
        identifier_pattern="P-\\d{3}",
        record_count=10,
        fields=[
            DiscoveredField(raw_label="Policy ID", inferred_type="identifier", confidence=0.95),
            DiscoveredField(raw_label="Title", inferred_type="text", confidence=0.90),
            DiscoveredField(raw_label="Effective Date", inferred_type="date", confidence=0.85),
        ],
    )
    assert entity.discovered_label == "Policy"
    assert len(entity.fields) == 3
    assert entity.record_count == 10


def test_schema_map_with_relationships() -> None:
    """Test SchemaMap with entity relationships."""
    from agent1.models.schema_map import DiscoveredRelationship
    
    control_entity = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    policy_entity = DiscoveredEntity(
        discovered_label="Policy",
        record_count=3,
        fields=[
            DiscoveredField(raw_label="Policy ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    relationship = DiscoveredRelationship(
        from_entity="Control",
        from_field="Control ID",
        to_entity="Policy",
        to_field="Policy ID",
        cardinality="many_to_one",
    )
    schema_map = SchemaMap(
        document_format="grc_export",
        structural_pattern="horizontal_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[control_entity, policy_entity],
        relationships=[relationship],
        total_records_estimated=8,
        schema_version="test",
        avg_confidence=0.95,
    )
    assert len(schema_map.entities) == 2
    assert len(schema_map.relationships) == 1
    assert schema_map.relationships[0].cardinality == "many_to_one"


def test_schema_hash_changes_with_content() -> None:
    """Test schema hash changes when content changes."""
    entity1 = DiscoveredEntity(
        discovered_label="Control",
        record_count=5,
        fields=[
            DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    schema_map1 = SchemaMap(
        document_format="test",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity1],
        relationships=[],
        total_records_estimated=5,
        schema_version="",
        avg_confidence=0.95,
    )
    hash1 = compute_schema_hash(schema_map1)
    
    entity2 = DiscoveredEntity(
        discovered_label="Policy",
        record_count=3,
        fields=[
            DiscoveredField(raw_label="Policy ID", inferred_type="identifier", confidence=0.95),
        ],
    )
    schema_map2 = SchemaMap(
        document_format="test",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[entity2],
        relationships=[],
        total_records_estimated=3,
        schema_version="",
        avg_confidence=0.95,
    )
    hash2 = compute_schema_hash(schema_map2)
    
    assert hash1 != hash2
