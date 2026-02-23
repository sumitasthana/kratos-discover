"""GRC Component models for the Agent1 pipeline.

Defines Pydantic models for Policy, Risk, and Control components extracted
from GRC library documents. These components are extracted by Node 3.5
(GRCComponentExtractorNode) and linked to requirements in Node 4 (Atomizer).
"""
from __future__ import annotations

from typing import Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class GRCComponentBase(BaseModel):
    """Shared base for all GRC components."""
    model_config = ConfigDict(extra="allow")
    
    component_type: str
    component_id: Optional[str] = None
    source_chunk_id: Optional[str] = None
    source_location: Optional[str] = None
    validation_errors: List[str] = Field(default_factory=list)


class PolicyComponent(GRCComponentBase):
    """Policy component extracted from GRC library documents."""
    component_type: str = Field(default="policy")
    
    # Core identification
    component_title: Optional[str] = None
    component_owner: Optional[str] = None
    
    # Policy details
    policy_objective: Optional[str] = None
    approval_authority: Optional[str] = None
    effective_date: Optional[str] = None
    review_cycle: Optional[str] = None
    policy_statement: Optional[str] = None
    scope: Optional[str] = None
    
    # Requirements and responsibilities
    detailed_requirements: Optional[Any] = None  # Can be string or list
    roles_responsibilities: Optional[Any] = None  # Can be string or list
    
    # Relationships
    related_regulations: Optional[Any] = None  # Can be string or list
    grc_platform_module: Optional[str] = None
    related_controls: Optional[List[str]] = Field(default_factory=list)
    related_risks: Optional[List[str]] = Field(default_factory=list)
    
    # Source tracking
    source_table_identifier: Optional[str] = None


class RiskComponent(GRCComponentBase):
    """Risk component extracted from GRC library documents."""
    component_type: str = Field(default="risk")
    
    # Core identification
    risk_description: Optional[str] = None
    risk_owner: Optional[str] = None
    risk_category: Optional[str] = None
    
    # Risk assessment
    inherent_risk_rating: Optional[str] = None
    residual_risk_rating: Optional[str] = None
    
    # Lifecycle
    effective_date: Optional[str] = None
    review_cycle: Optional[str] = None
    
    # Relationships
    grc_platform_module: Optional[str] = None
    related_policies: Optional[List[str]] = Field(default_factory=list)
    mitigation_controls: Optional[List[str]] = Field(default_factory=list)
    related_controls: Optional[List[str]] = Field(default_factory=list)
    
    # Source tracking
    source_table_identifier: Optional[str] = None


class ControlComponent(GRCComponentBase):
    """Control component extracted from GRC library documents."""
    component_type: str = Field(default="control")
    
    # Core identification
    control_description: Optional[str] = None
    control_owner: Optional[str] = None
    
    # Control characteristics
    control_type: Optional[Any] = None  # Can be string or dict {nature, automation}
    operating_frequency: Optional[str] = None
    testing_frequency: Optional[str] = None
    evidence: Optional[Any] = None  # Can be string or list
    
    # Lifecycle
    effective_date: Optional[str] = None
    review_cycle: Optional[str] = None
    
    # Relationships
    grc_platform_module: Optional[str] = None
    related_policies: Optional[List[str]] = Field(default_factory=list)
    related_risks: Optional[List[str]] = Field(default_factory=list)
    
    # Source tracking
    source_table_identifier: Optional[str] = None


class GRCComponentsResponse(BaseModel):
    """Aggregated response from GRC component extraction."""
    policies: List[PolicyComponent] = Field(default_factory=list)
    risks: List[RiskComponent] = Field(default_factory=list)
    controls: List[ControlComponent] = Field(default_factory=list)
    cross_reference_index: dict[str, List[str]] = Field(
        default_factory=dict,
        description="Maps component_id to list of related component_ids"
    )
    extraction_summary: dict[str, Any] = Field(default_factory=dict)
