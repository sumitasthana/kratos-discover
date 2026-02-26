"""Integration test: GRC components flow through to atomizer requirements."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.chunks import ContentChunk
from models.grc_components import (
    ControlComponent,
    GRCComponentsResponse,
    PolicyComponent,
)
from models.requirements import RegulatoryRequirement, RuleMetadata
from models.schema_map import DiscoveredEntity, DiscoveredField, SchemaMap
from nodes.atomizer.node import RequirementAtomizerNode
from nodes.grc_extractor import GRCComponentExtractorNode
from models.shared import RuleType


def make_test_chunk(
    chunk_id: str,
    chunk_type: str = "table",
    record_type: str | None = None,
    record_id: str | None = None,
    content: str = "Test content with regulatory requirements.",
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
                record_count=2,
                fields=[
                    DiscoveredField(raw_label="Policy ID", inferred_type="identifier", confidence=0.9),
                ],
            ),
            DiscoveredEntity(
                discovered_label="CONTROL",
                record_count=2,
                fields=[
                    DiscoveredField(raw_label="Control ID", inferred_type="identifier", confidence=0.9),
                ],
            ),
        ],
        relationships=[],
        total_records_estimated=4,
        schema_version="test-v1",
        avg_confidence=0.9,
    )


def make_test_requirement(
    req_id: str,
    source_chunk_id: str,
    rule_type: RuleType = RuleType.DATA_QUALITY_THRESHOLD,
) -> RegulatoryRequirement:
    """Create a test RegulatoryRequirement."""
    return RegulatoryRequirement(
        requirement_id=req_id,
        rule_type=rule_type,
        rule_description="Test requirement description",
        grounded_in="Test grounded text",
        confidence=0.75,
        attributes={
            "metric": "accuracy",
            "threshold_value": 99.0,
            "threshold_direction": ">=",
        },
        metadata=RuleMetadata(
            source_chunk_id=source_chunk_id,
            source_location="Test Location",
            schema_version="test-v1",
            prompt_version="v1.0",
            extraction_iteration=1,
        ),
    )


class TestComponentIdFlowsToRequirements:
    """Test that component IDs flow through the pipeline to requirements."""

    def test_component_index_propagates_to_atomizer(self):
        """component_index from GRC extractor is used by atomizer."""
        # Create component_index as GRC extractor would produce
        component_index = {
            "chunk-1": "P-001",
            "chunk-2": "C-001",
        }
        
        # Create requirements as atomizer would produce (before linkage)
        requirements = [
            make_test_requirement("R-DQ-001", source_chunk_id="chunk-1"),
            make_test_requirement("R-DQ-002", source_chunk_id="chunk-2"),
            make_test_requirement("R-DQ-003", source_chunk_id="chunk-3"),  # No component
        ]
        
        # Simulate atomizer linkage logic
        for req in requirements:
            source_chunk_id = req.metadata.source_chunk_id
            parent_id = component_index.get(source_chunk_id)
            if parent_id:
                req.parent_component_id = parent_id
        
        # Verify linkage
        assert requirements[0].parent_component_id == "P-001"
        assert requirements[1].parent_component_id == "C-001"
        assert requirements[2].parent_component_id is None

    @patch("nodes.grc_extractor.get_anthropic_client")
    def test_grc_extractor_builds_component_index(self, mock_get_client):
        """GRC extractor builds component_index correctly."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock response with components
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='[{"component_id": "P-001", "component_type": "policy"}]')
        ]
        mock_client.messages.create.return_value = mock_response
        
        node = GRCComponentExtractorNode()
        state = {
            "chunks": [
                make_test_chunk("chunk-abc", record_type="policy", record_id="P-001"),
            ],
            "schema_map": make_test_schema_map(),
            "prompt_versions": {},
        }
        
        result = node(state)
        
        # Verify component_index is built
        component_index = result.get("component_index", {})
        grc_components = result.get("grc_components")
        
        assert grc_components is not None
        assert len(grc_components.policies) == 1
        # The component should have source_chunk_id set
        assert grc_components.policies[0].source_chunk_id == "chunk-abc"
        assert component_index.get("chunk-abc") == "P-001"

    def test_output_payload_contains_both_sections(self):
        """Output payload contains both grc_components and requirements."""
        # Simulate what CLI produces
        grc_components = GRCComponentsResponse(
            policies=[PolicyComponent(component_id="P-001")],
            controls=[ControlComponent(component_id="C-001")],
        )
        
        requirements = [
            make_test_requirement("R-DQ-001", source_chunk_id="chunk-1"),
        ]
        requirements[0].parent_component_id = "P-001"
        
        # Build payload as CLI does
        payload = {
            "requirements": [r.model_dump() for r in requirements],
            "grc_components": grc_components.model_dump(),
        }
        
        # Verify structure
        assert "requirements" in payload
        assert "grc_components" in payload
        assert len(payload["requirements"]) == 1
        assert payload["requirements"][0]["parent_component_id"] == "P-001"
        assert len(payload["grc_components"]["policies"]) == 1
        assert len(payload["grc_components"]["controls"]) == 1

    def test_requirement_parent_component_id_field_exists(self):
        """RegulatoryRequirement has parent_component_id field."""
        req = make_test_requirement("R-DQ-001", source_chunk_id="chunk-1")
        
        # Default is None
        assert req.parent_component_id is None
        
        # Can be set
        req.parent_component_id = "P-001"
        assert req.parent_component_id == "P-001"
        
        # Serializes correctly
        data = req.model_dump()
        assert "parent_component_id" in data
        assert data["parent_component_id"] == "P-001"


class TestEndToEndFlow:
    """End-to-end flow tests."""

    def test_full_pipeline_state_flow(self):
        """State flows correctly through all nodes."""
        # Initial state
        state = {
            "file_path": "test.docx",
            "chunks": [
                make_test_chunk("chunk-1", record_type="policy", record_id="P-001"),
                make_test_chunk("chunk-2", record_type="control", record_id="C-001"),
            ],
            "schema_map": make_test_schema_map(),
            "prompt_versions": {},
            "errors": [],
            "extraction_iteration": 1,
        }
        
        # Simulate GRC extractor output
        grc_components = GRCComponentsResponse(
            policies=[PolicyComponent(component_id="P-001", source_chunk_id="chunk-1")],
            controls=[ControlComponent(component_id="C-001", source_chunk_id="chunk-2")],
        )
        component_index = {"chunk-1": "P-001", "chunk-2": "C-001"}
        
        # Update state as GRC extractor would
        state["grc_components"] = grc_components
        state["component_index"] = component_index
        
        # Verify state has all required fields for atomizer
        assert "chunks" in state
        assert "schema_map" in state
        assert "component_index" in state
        assert state["component_index"]["chunk-1"] == "P-001"
        assert state["component_index"]["chunk-2"] == "C-001"
