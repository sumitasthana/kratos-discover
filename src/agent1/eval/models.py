"""Pydantic models for Eval node output."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TestabilityIssue(BaseModel):
    """Issue found during testability check."""
    req_id: str
    issues: list[str]
    severity: Literal["low", "medium", "high"]


class GroundingIssue(BaseModel):
    """Issue found during grounding check."""
    req_id: str
    issues: list[str]
    severity: Literal["low", "medium", "high"]
    grounding_classification: str = ""  # EXACT, PARAPHRASE, INFERENCE


class HallucinationFlag(BaseModel):
    """Hallucination risk flag."""
    req_id: str
    flags: list[str]
    risk: Literal["low", "medium", "high", "critical"]
    confidence: float = 0.0
    iteration: int = 1


class SchemaComplianceIssue(BaseModel):
    """Schema compliance issue."""
    req_id: str
    rule_type: str
    missing_fields: list[str]
    invalid_fields: list[str]
    severity: Literal["low", "medium", "high"]


class PotentialDuplicate(BaseModel):
    """Potential duplicate pair."""
    req_id_a: str
    req_id_b: str
    similarity: float
    rule_type: str


class EvalReport(BaseModel):
    """Diagnostic output from Eval node."""
    
    # Counts & coverage
    total_chunks: int = 0
    chunks_processed: int = 0
    chunks_with_zero_extractions: list[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0
    
    # Requirement metrics
    total_requirements: int = 0
    requirements_by_type: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    confidence_distribution: dict[str, int] = Field(default_factory=dict)  # {"0.90-0.99": 5, ...}
    
    # Quality checks
    testability_issues: list[TestabilityIssue] = Field(default_factory=list)
    grounding_issues: list[GroundingIssue] = Field(default_factory=list)
    hallucination_flags: list[HallucinationFlag] = Field(default_factory=list)
    schema_compliance_issues: list[SchemaComplianceIssue] = Field(default_factory=list)
    
    # Deduplication metrics
    unique_requirement_count: int = 0
    potential_duplicates: list[PotentialDuplicate] = Field(default_factory=list)
    dedup_ratio: float = 1.0
    
    # Schema coverage
    schema_entities: int = 0
    schema_coverage: dict[str, int] = Field(default_factory=dict)
    
    # Pass/Fail decision signals
    failure_type: Literal["none", "coverage", "testability", "grounding", "schema", "dedup", "hallucination", "multi"] = "none"
    failure_severity: Literal["low", "medium", "high", "critical"] = "low"
    is_retryable: bool = False
    
    # Actionable feedback
    remediation_suggestions: list[str] = Field(default_factory=list)
    
    # Metadata
    eval_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    extraction_iteration: int = 1
    prompt_version: str = ""
    
    # Summary scores
    overall_quality_score: float = 0.0  # 0.0-1.0 composite score
    
    def to_router_signal(self) -> dict[str, Any]:
        """Generate signal for Router decision."""
        return {
            "failure_type": self.failure_type,
            "failure_severity": self.failure_severity,
            "is_retryable": self.is_retryable,
            "coverage_ratio": self.coverage_ratio,
            "avg_confidence": self.avg_confidence,
            "overall_quality_score": self.overall_quality_score,
        }
