"""Tests for GRC component models."""
from __future__ import annotations

import pytest

from agent1.models.grc_components import (
    ControlComponent,
    GRCComponentBase,
    GRCComponentsResponse,
    PolicyComponent,
    RiskComponent,
)


class TestPolicyComponent:
    """Tests for PolicyComponent model."""

    def test_policy_component_defaults(self):
        """PolicyComponent() creates valid object with defaults."""
        policy = PolicyComponent()
        
        assert policy.component_type == "policy"
        assert policy.component_id is None
        assert policy.source_chunk_id is None
        assert policy.validation_errors == []
        assert policy.related_controls == []
        assert policy.related_risks == []

    def test_policy_component_with_all_fields(self):
        """PolicyComponent with all fields populated."""
        policy = PolicyComponent(
            component_id="P-001",
            component_title="Data Quality Policy",
            component_owner="Chief Data Officer",
            policy_objective="Ensure data accuracy",
            approval_authority="Board of Directors",
            effective_date="2024-01-01",
            review_cycle="Annual",
            policy_statement="All data must be accurate",
            scope="Enterprise-wide",
            detailed_requirements=["Req 1", "Req 2"],
            roles_responsibilities=["Role 1", "Role 2"],
            related_regulations=["FDIC 370"],
            grc_platform_module="Archer",
            related_controls=["C-001", "C-002"],
            related_risks=["R-001"],
            source_table_identifier="Table 1",
            source_chunk_id="chunk-abc",
            source_location="Page 5",
        )
        
        assert policy.component_id == "P-001"
        assert policy.component_title == "Data Quality Policy"
        assert policy.related_controls == ["C-001", "C-002"]
        assert policy.source_chunk_id == "chunk-abc"


class TestRiskComponent:
    """Tests for RiskComponent model."""

    def test_risk_component_required_fields(self):
        """RiskComponent with all None optionals is valid."""
        risk = RiskComponent(component_id="R-001")
        
        assert risk.component_type == "risk"
        assert risk.component_id == "R-001"
        assert risk.risk_description is None
        assert risk.inherent_risk_rating is None
        assert risk.related_policies == []
        assert risk.mitigation_controls == []

    def test_risk_component_with_ratings(self):
        """RiskComponent with risk ratings."""
        risk = RiskComponent(
            component_id="R-001",
            risk_description="Data breach risk",
            risk_category="Operational",
            inherent_risk_rating="High",
            residual_risk_rating="Medium",
            mitigation_controls=["C-001", "C-002"],
        )
        
        assert risk.inherent_risk_rating == "High"
        assert risk.residual_risk_rating == "Medium"
        assert len(risk.mitigation_controls) == 2


class TestControlComponent:
    """Tests for ControlComponent model."""

    def test_control_component_control_type_string(self):
        """control_type can be a string."""
        control = ControlComponent(
            component_id="C-001",
            control_type="Preventive",
        )
        
        assert control.control_type == "Preventive"

    def test_control_component_control_type_dict(self):
        """control_type can be a dict with nature and automation."""
        control = ControlComponent(
            component_id="C-001",
            control_type={"nature": "Preventive", "automation": "Automated"},
        )
        
        assert control.control_type == {"nature": "Preventive", "automation": "Automated"}

    def test_control_component_all_fields(self):
        """ControlComponent with all fields populated."""
        control = ControlComponent(
            component_id="C-001",
            control_description="Access control",
            control_owner="IT Security",
            control_type={"nature": "Preventive", "automation": "Automated"},
            operating_frequency="Continuous",
            testing_frequency="Quarterly",
            evidence="System logs",
            effective_date="2024-01-01",
            review_cycle="Annual",
            grc_platform_module="Archer",
            related_policies=["P-001"],
            related_risks=["R-001", "R-002"],
            source_table_identifier="Table 3",
        )
        
        assert control.component_id == "C-001"
        assert control.related_policies == ["P-001"]
        assert len(control.related_risks) == 2


class TestGRCComponentsResponse:
    """Tests for GRCComponentsResponse model."""

    def test_empty_response(self):
        """Empty GRCComponentsResponse is valid."""
        response = GRCComponentsResponse()
        
        assert response.policies == []
        assert response.risks == []
        assert response.controls == []
        assert response.cross_reference_index == {}
        assert response.extraction_summary == {}

    def test_grc_response_cross_reference_index(self):
        """Build and validate cross-ref index."""
        response = GRCComponentsResponse(
            policies=[PolicyComponent(component_id="P-001", related_controls=["C-001"])],
            risks=[RiskComponent(component_id="R-001", mitigation_controls=["C-001"])],
            controls=[ControlComponent(component_id="C-001", related_policies=["P-001"])],
            cross_reference_index={
                "P-001": ["C-001"],
                "R-001": ["C-001"],
                "C-001": ["P-001"],
            },
        )
        
        assert "P-001" in response.cross_reference_index
        assert "C-001" in response.cross_reference_index["P-001"]
        assert len(response.policies) == 1
        assert len(response.controls) == 1

    def test_component_base_inherits_to_all(self):
        """All three types have source_chunk_id and validation_errors from base."""
        policy = PolicyComponent(source_chunk_id="chunk-1", validation_errors=["err1"])
        risk = RiskComponent(source_chunk_id="chunk-2", validation_errors=["err2"])
        control = ControlComponent(source_chunk_id="chunk-3", validation_errors=["err3"])
        
        assert policy.source_chunk_id == "chunk-1"
        assert risk.source_chunk_id == "chunk-2"
        assert control.source_chunk_id == "chunk-3"
        
        assert policy.validation_errors == ["err1"]
        assert risk.validation_errors == ["err2"]
        assert control.validation_errors == ["err3"]

    def test_response_with_extraction_summary(self):
        """GRCComponentsResponse with extraction summary."""
        response = GRCComponentsResponse(
            policies=[PolicyComponent(component_id="P-001")],
            extraction_summary={
                "total_policies": 1,
                "total_risks": 0,
                "total_controls": 0,
                "validation_errors": [],
            },
        )
        
        assert response.extraction_summary["total_policies"] == 1
        assert response.extraction_summary["validation_errors"] == []
