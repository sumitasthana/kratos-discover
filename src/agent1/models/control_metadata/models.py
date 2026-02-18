"""Data models for control metadata.

Contains the ControlMetadata dataclass and related models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ControlMetadata:
    """Operationalization metadata for a regulatory requirement.
    
    Source tracking (CF-12, CF-13):
    - evidence_type_source: "extracted" | "default_template"
    - system_mapping_source: "extracted" | "keyword_inferred" | "default_template"
    """
    control_objective: str = ""
    risk_addressed: list[str] = field(default_factory=list)
    test_procedure: str = ""
    control_owner: str = ""
    automated: str = "manual"  # automated, manual, hybrid
    evidence_type: list[str] = field(default_factory=list)
    evidence_type_source: str = "default_template"  # CF-12: extracted | default_template
    system_mapping: list[str] = field(default_factory=list)
    system_mapping_source: str = "default_template"  # CF-13: extracted | keyword_inferred | default_template
    system_mapping_keywords: list[str] = field(default_factory=list)  # CF-13: keywords that triggered inference
    exception_threshold: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "control_objective": self.control_objective,
            "risk_addressed": self.risk_addressed,
            "test_procedure": self.test_procedure,
            "control_owner": self.control_owner,
            "automated": self.automated,
            "evidence_type": self.evidence_type,
            "evidence_type_source": self.evidence_type_source,
            "system_mapping": self.system_mapping,
            "system_mapping_source": self.system_mapping_source,
            "system_mapping_keywords": self.system_mapping_keywords,
            "exception_threshold": self.exception_threshold,
        }
    
    def is_complete(self) -> bool:
        """Check if all required metadata fields are populated."""
        return bool(
            self.control_objective and
            self.risk_addressed and
            self.test_procedure and
            self.control_owner and
            self.automated and
            self.evidence_type
        )


@dataclass
class ExceptionTier:
    """Exception escalation tier."""
    condition: str
    action: str
    sla_remediation: str = ""
