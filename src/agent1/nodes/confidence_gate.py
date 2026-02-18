from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
import yaml
from pathlib import Path
import structlog

from agent1.models.state import Phase1State

logger = structlog.get_logger(__name__)

CONFIG_FILE = Path(__file__).parent.parent / "config" / "gate_config.yaml"


@dataclass
class GateDecision:
    """Structured gate decision with rationale (CF-8)."""
    decision: Literal["accept", "human_review", "reject"]
    score: float
    thresholds_applied: dict[str, float] = field(default_factory=dict)
    failing_checks: list[str] = field(default_factory=list)
    conditional_flags: list[str] = field(default_factory=list)
    rationale: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "score": round(self.score, 3),
            "thresholds_applied": self.thresholds_applied,
            "failing_checks": self.failing_checks,
            "conditional_flags": self.conditional_flags,
            "rationale": self.rationale,
        }


def load_gate_config() -> dict:
    """Load confidence thresholds from config."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    return {
        "thresholds": {
            "default": {
                "auto_accept": 0.85,
                "human_review": 0.50,
                "min_schema_compliance": 0.50,
                "min_coverage": 0.60,
            }
        }
    }


def check_confidence(state: Phase1State) -> GateDecision:
    """LangGraph conditional edge: routes based on schema confidence.
    
    CF-8: Returns structured GateDecision instead of bare string.
    CF-7b: Adds schema_compliance threshold check.
    """
    schema_map = state.get("schema_map")
    if schema_map is None:
        logger.warning("confidence_gate_no_schema")
        return GateDecision(
            decision="reject",
            score=0.0,
            failing_checks=["no_schema_map"],
            rationale="No schema map available for evaluation.",
        )

    avg_conf = schema_map.avg_confidence
    doc_format = schema_map.document_format

    config = load_gate_config()
    thresholds = config.get("thresholds", {}).get(
        doc_format, config.get("thresholds", {}).get("default", {})
    )

    auto_accept = thresholds.get("auto_accept", 0.85)
    human_review = thresholds.get("human_review", 0.50)
    min_schema_compliance = thresholds.get("min_schema_compliance", 0.50)
    min_coverage = thresholds.get("min_coverage", 0.60)
    
    thresholds_applied = {
        "auto_accept": auto_accept,
        "human_review": human_review,
        "min_schema_compliance": min_schema_compliance,
        "min_coverage": min_coverage,
    }
    
    failing_checks: list[str] = []
    conditional_flags: list[str] = []
    
    # Check schema confidence
    if avg_conf < human_review:
        failing_checks.append(f"avg_confidence={avg_conf:.3f} < {human_review}")
    elif avg_conf < auto_accept:
        conditional_flags.append(f"avg_confidence={avg_conf:.3f} < {auto_accept}")
    
    # CF-7b: Check eval_report metrics if available
    eval_report = state.get("eval_report")
    if eval_report:
        schema_issues = len(eval_report.get("schema_compliance_issues", []))
        total_reqs = eval_report.get("total_requirements", 1)
        schema_ratio = 1.0 - (schema_issues / max(total_reqs, 1))
        
        if schema_ratio < min_schema_compliance:
            failing_checks.append(f"schema_compliance={schema_ratio:.1%} < {min_schema_compliance:.1%}")
        
        coverage = eval_report.get("coverage_ratio", 1.0)
        if coverage < min_coverage:
            failing_checks.append(f"coverage={coverage:.1%} < {min_coverage:.1%}")
        
        if eval_report.get("testability_issues"):
            conditional_flags.append(f"testability_issues={len(eval_report['testability_issues'])}")
        if eval_report.get("hallucination_flags"):
            conditional_flags.append(f"hallucination_flags={len(eval_report['hallucination_flags'])}")
    
    # Determine decision
    if failing_checks:
        decision = "reject"
        rationale = f"Failed checks: {'; '.join(failing_checks)}"
    elif avg_conf >= auto_accept and not conditional_flags:
        decision = "accept"
        rationale = f"All thresholds met. Confidence={avg_conf:.3f}"
    elif avg_conf >= human_review:
        decision = "human_review"
        rationale = f"Needs review: {'; '.join(conditional_flags) if conditional_flags else 'confidence below auto_accept'}"
    else:
        decision = "reject"
        rationale = f"Confidence {avg_conf:.3f} below minimum {human_review}"
    
    logger.info(
        f"confidence_gate_{decision}",
        avg_confidence=avg_conf,
        failing_checks=failing_checks,
        conditional_flags=conditional_flags,
    )
    
    return GateDecision(
        decision=decision,
        score=avg_conf,
        thresholds_applied=thresholds_applied,
        failing_checks=failing_checks,
        conditional_flags=conditional_flags,
        rationale=rationale,
    )
