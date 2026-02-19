"""Tests for GRC Component Extractor node."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent1.models.chunks import ContentChunk
from agent1.models.grc_components import (
    ControlComponent,
    GRCComponentsResponse,
    PolicyComponent,
    RiskComponent,
)
from agent1.models.schema_map import DiscoveredEntity, DiscoveredField, SchemaMap
from agent1.nodes.grc_extractor import GRCComponentExtractorNode


def make_test_chunk(
    chunk_id: str,
    chunk_type: str = "table",
    record_type: str | None = None,
    record_id: str | None = None,
    content: str = "Test content",
) -> ContentChunk:
    """Create a test ContentChunk."""
    annotations = {}
    if record_type:
        annotations["record_type"] = record_type
    if record_id:
        annotations["record_id"] = record_id
    
    return ContentChunk(
        chunk_id=chunk_id,
        chunk_type=chunk_type,
        content_text=content,
        source_location="Test Location",
        char_count=len(content),
        annotations=annotations,
    )


def make_test_schema_map() -> SchemaMap:
    """Create a test SchemaMap."""
    return SchemaMap(
        document_format="docx",
        structural_pattern="vertical_key_value_tables",
        structural_confidence=0.9,
        inferred_document_category="grc_library",
        entities=[
            DiscoveredEntity(
                discovered_label="POLICY",
                record_count=10,
                fields=[
                    DiscoveredField(raw_label="Policy ID", inferred_type="identifier", confidence=0.9),
                    DiscoveredField(raw_label="Policy Title", inferred_type="text", confidence=0.9),
                ],
            ),
            DiscoveredEntity(
                discovered_label="CONTROL",
                record_count=25,
                fields=[
                    DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.9),
                    DiscoveredField(raw_label="Control Description", inferred_type="text", confidence=0.9),
                ],
            ),
        ],
        relationships=[],
        total_records_estimated=35,
        schema_version="test-v1",
        avg_confidence=0.9,
    )


class TestGRCExtractorNode:
    """Tests for GRCComponentExtractorNode."""

    def test_empty_chunks_returns_empty(self):
        """Input: state with chunks=[], schema_map=valid. Returns empty result."""
        node = GRCComponentExtractorNode()
        state = {
            "chunks": [],
            "schema_map": make_test_schema_map(),
        }
        
        result = node(state)
        
        grc = result.get("grc_components")
        assert grc is not None
        assert grc.policies == []
        assert grc.risks == []
        assert grc.controls == []
        assert result.get("component_index") == {}

    def test_no_schema_map_returns_empty(self):
        """Input: state with chunks=[...], schema_map=None. Returns empty with error."""
        node = GRCComponentExtractorNode()
        state = {
            "chunks": [make_test_chunk("chunk-1", record_type="policy")],
            "schema_map": None,
        }
        
        result = node(state)
        
        assert "errors" in result
        assert "No schema map provided" in result["errors"]

    def test_prose_chunks_skipped(self):
        """Only table chunks with record_type are processed."""
        node = GRCComponentExtractorNode()
        
        # Mix of table and prose chunks
        chunks = [
            make_test_chunk("chunk-1", chunk_type="table", record_type="policy"),
            make_test_chunk("chunk-2", chunk_type="prose"),  # No record_type
            make_test_chunk("chunk-3", chunk_type="prose", record_type="risk"),  # Prose with record_type
            make_test_chunk("chunk-4", chunk_type="table"),  # Table without record_type
        ]
        
        extractable = node._get_extractable_chunks(chunks)
        
        # Only chunk-1 should be included (table with record_type)
        assert "policy" in extractable
        assert len(extractable["policy"]) == 1
        assert extractable["policy"][0].chunk_id == "chunk-1"

    @patch.object(GRCComponentExtractorNode, "_extract_components")
    def test_component_index_built_correctly(self, mock_extract):
        """component_index maps chunk_id to component_id."""
        # Mock extraction to return a policy with source_chunk_id
        mock_extract.return_value = [
            PolicyComponent(
                component_id="P-001",
                source_chunk_id="chunk-abc",
            )
        ]
        
        node = GRCComponentExtractorNode()
        state = {
            "chunks": [
                make_test_chunk("chunk-abc", record_type="policy", record_id="P-001"),
            ],
            "schema_map": make_test_schema_map(),
        }
        
        result = node(state)
        
        component_index = result.get("component_index", {})
        assert component_index.get("chunk-abc") == "P-001"

    def test_list_normalization(self):
        """Comma-separated strings are normalized to arrays."""
        node = GRCComponentExtractorNode()
        
        # Test comma-separated
        result = node._normalize_list("C-001, C-002, C-003")
        assert result == ["C-001", "C-002", "C-003"]
        
        # Test semicolon-separated
        result = node._normalize_list("C-001; C-002; C-003")
        assert result == ["C-001", "C-002", "C-003"]
        
        # Test already a list
        result = node._normalize_list(["C-001", "C-002"])
        assert result == ["C-001", "C-002"]
        
        # Test None
        result = node._normalize_list(None)
        assert result == []

    def test_control_type_normalization(self):
        """Control type 'Nature / Automation' is parsed correctly."""
        node = GRCComponentExtractorNode()
        
        # Test slash-separated
        result = node._normalize_control_type_field("Preventive / Automated")
        assert result == {"nature": "Preventive", "automation": "Automated"}
        
        # Test already a dict
        result = node._normalize_control_type_field({"nature": "Detective", "automation": "Manual"})
        assert result == {"nature": "Detective", "automation": "Manual"}
        
        # Test simple string
        result = node._normalize_control_type_field("Preventive")
        assert result == "Preventive"
        
        # Test None
        result = node._normalize_control_type_field(None)
        assert result == {}

    def test_cross_reference_validation(self):
        """Cross-reference validation flags missing references."""
        node = GRCComponentExtractorNode()
        
        grc = GRCComponentsResponse(
            policies=[
                PolicyComponent(
                    component_id="P-001",
                    related_controls=["C-001", "C-999"],  # C-999 doesn't exist
                )
            ],
            controls=[
                ControlComponent(component_id="C-001"),
            ],
        )
        
        errors = node._validate_cross_references(grc)
        
        assert len(errors) == 1
        assert "C-999" in errors[0]
        assert "P-001" in errors[0]

    def test_build_cross_reference_index(self):
        """Cross-reference index is built correctly."""
        node = GRCComponentExtractorNode()
        
        grc = GRCComponentsResponse(
            policies=[
                PolicyComponent(
                    component_id="P-001",
                    related_controls=["C-001", "C-002"],
                    related_risks=["R-001"],
                )
            ],
            risks=[
                RiskComponent(
                    component_id="R-001",
                    mitigation_controls=["C-001"],
                )
            ],
            controls=[
                ControlComponent(
                    component_id="C-001",
                    related_policies=["P-001"],
                )
            ],
        )
        
        index = node._build_cross_reference_index(grc)
        
        assert "P-001" in index
        assert set(index["P-001"]) == {"C-001", "C-002", "R-001"}
        assert "R-001" in index
        assert "C-001" in index["R-001"]


class TestGRCExtractorIntegration:
    """Integration tests with mocked LLM calls."""

    @patch("agent1.nodes.grc_extractor.get_anthropic_client")
    def test_extract_components_parses_response(self, mock_get_client):
        """LLM response is parsed into components."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='[{"component_id": "P-001", "component_type": "policy", "component_title": "Test Policy"}]')
        ]
        mock_client.messages.create.return_value = mock_response
        
        node = GRCComponentExtractorNode()
        state = {
            "chunks": [
                make_test_chunk("chunk-1", record_type="policy", record_id="P-001"),
            ],
            "schema_map": make_test_schema_map(),
            "prompt_versions": {},
        }
        
        result = node(state)
        
        grc = result.get("grc_components")
        assert grc is not None
        assert len(grc.policies) == 1
        assert grc.policies[0].component_id == "P-001"
        assert grc.policies[0].component_title == "Test Policy"
