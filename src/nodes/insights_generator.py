"""Insights Generator - Post-processing node that produces narrative insights from extraction results.

Analyzes the extraction output and generates human-readable insights without additional LLM calls.
Focuses on quality assessment, risk flags, automation readiness, and actionable recommendations.
"""
from __future__ import annotations

import structlog
from dataclasses import dataclass
from typing import Any

logger = structlog.get_logger(__name__)


@dataclass
class InsightsResult:
    """Structured insights output."""
    quality_assessment: dict[str, Any]
    risk_flags: list[dict[str, Any]]
    rule_type_distribution: dict[str, Any]
    hallucination_risk: dict[str, Any]
    confidence_distribution: dict[str, Any]
    recommendations: list[str]


def generate_insights(requirements: list[Any], extraction_metadata: dict[str, Any], gate_decision: dict[str, Any]) -> InsightsResult:
    """
    Generate narrative insights from extraction results.
    
    Args:
        requirements: List of RegulatoryRequirement objects
        extraction_metadata: Extraction metadata dict
        gate_decision: Gate decision dict
    
    Returns:
        InsightsResult with quality, risk, automation, confidence, and recommendations
    """
    
    # =========================================================================
    # 1. QUALITY ASSESSMENT
    # =========================================================================
    
    total_reqs = len(requirements)
    
    # Schema completeness
    reqs_with_all_required = sum(
        1 for req in requirements 
        if not req.attributes.get("_schema_validation") or 
        req.attributes.get("_schema_validation", {}).get("status") == "valid"
    )
    schema_completeness = (reqs_with_all_required / total_reqs * 100) if total_reqs > 0 else 0
    
    # Grounding quality (all should be EXACT based on fixes)
    exact_grounding = sum(
        1 for req in requirements 
        if req.attributes.get("_grounding_classification") == "EXACT"
    )
    grounding_quality = (exact_grounding / total_reqs * 100) if total_reqs > 0 else 0
    
    # Data source coverage
    reqs_with_data_source = sum(
        1 for req in requirements 
        if req.attributes.get("data_source")
    )
    data_source_coverage = (reqs_with_data_source / total_reqs * 100) if total_reqs > 0 else 0
    
    quality_assessment = {
        "schema_completeness_pct": round(schema_completeness, 1),
        "grounding_quality_pct": round(grounding_quality, 1),
        "data_source_coverage_pct": round(data_source_coverage, 1),
        "overall_quality_tier": _get_quality_tier(schema_completeness, grounding_quality, data_source_coverage),
    }
    
    # =========================================================================
    # 2. RISK FLAGS
    # =========================================================================
    
    risk_flags = []
    
    # Flag: Low data source coverage
    if data_source_coverage < 80:
        risk_flags.append({
            "severity": "medium",
            "issue": "Data source coverage below 80%",
            "detail": f"{100 - data_source_coverage:.1f}% of requirements lack data_source mapping",
            "impact": "Asset lineage and impact analysis will be incomplete",
            "count": total_reqs - reqs_with_data_source,
        })
    
    # Flag: Schema issues
    reqs_with_schema_issues = sum(
        1 for req in requirements 
        if req.attributes.get("_schema_validation", {}).get("status") in ["rejected", "repaired"]
    )
    if reqs_with_schema_issues > 0:
        risk_flags.append({
            "severity": "low" if reqs_with_schema_issues < total_reqs * 0.1 else "medium",
            "issue": "Schema compliance issues detected",
            "detail": f"{reqs_with_schema_issues} requirements have missing or invalid fields",
            "impact": "May require manual review before Neo4j ingestion",
            "count": reqs_with_schema_issues,
        })
    
    # Flag: Fragment warnings
    fragment_warnings = sum(
        1 for req in requirements 
        if req.attributes.get("_fragment_warning")
    )
    if fragment_warnings > 0:
        risk_flags.append({
            "severity": "low",
            "issue": "Fragment context warnings",
            "detail": f"{fragment_warnings} requirements start with demonstrative pronouns (missing context)",
            "impact": "May need manual review for context validation",
            "count": fragment_warnings,
        })
    
    # Flag: Low confidence requirements
    low_confidence = sum(
        1 for req in requirements 
        if req.confidence < 0.65
    )
    if low_confidence > 0:
        risk_flags.append({
            "severity": "low",
            "issue": "Low confidence requirements",
            "detail": f"{low_confidence} requirements below 0.65 confidence threshold",
            "impact": "Recommend manual review for accuracy validation",
            "count": low_confidence,
        })
    
    # =========================================================================
    # 3. RULE TYPE DISTRIBUTION
    # =========================================================================
    
    rule_type_counts = {}
    for req in requirements:
        rule_type = req.rule_type.value if hasattr(req.rule_type, 'value') else str(req.rule_type)
        rule_type_counts[rule_type] = rule_type_counts.get(rule_type, 0) + 1
    
    rule_type_distribution = {}
    for rule_type, count in sorted(rule_type_counts.items()):
        percentage = round(count / total_reqs * 100, 1) if total_reqs > 0 else 0
        rule_type_distribution[rule_type] = {
            "count": count,
            "percentage": percentage,
        }
    
    # =========================================================================
    # 3.5 HALLUCINATION RISK ASSESSMENT
    # =========================================================================
    
    # Count hallucinations from eval_report if available
    hallucination_count = 0
    critical_hallucinations = 0
    high_hallucinations = 0
    
    # Try to get from eval_report in extraction_metadata
    eval_report = extraction_metadata.get("eval_report", {})
    hallucination_flags = eval_report.get("hallucination_flags", [])
    
    if hallucination_flags:
        hallucination_count = len(hallucination_flags)
        critical_hallucinations = sum(1 for h in hallucination_flags if isinstance(h, dict) and h.get("risk") == "critical")
        high_hallucinations = sum(1 for h in hallucination_flags if isinstance(h, dict) and h.get("risk") == "high")
    
    hallucination_pct = round(hallucination_count / total_reqs * 100, 1) if total_reqs > 0 else 0
    
    hallucination_risk = {
        "hallucination_pct": hallucination_pct,
        "hallucination_count": hallucination_count,
        "critical_count": critical_hallucinations,
        "high_count": high_hallucinations,
        "calculation_method": "Based on confidence score thresholds and grounding classification (INFERENCE vs QUOTE). Flagged if: (1) confidence < 0.70 on retry, (2) confidence < 0.60 on first pass, or (3) grounding classified as INFERENCE.",
    }
    
    # =========================================================================
    # 4. CONFIDENCE DISTRIBUTION
    # =========================================================================
    
    high_confidence = sum(1 for req in requirements if req.confidence >= 0.85)
    medium_confidence = sum(1 for req in requirements if 0.65 <= req.confidence < 0.85)
    low_confidence = sum(1 for req in requirements if req.confidence < 0.65)
    
    avg_confidence = sum(req.confidence for req in requirements) / total_reqs if total_reqs > 0 else 0
    
    confidence_distribution = {
        "high_confidence_count": high_confidence,
        "high_confidence_pct": round(high_confidence / total_reqs * 100, 1) if total_reqs > 0 else 0,
        "medium_confidence_count": medium_confidence,
        "medium_confidence_pct": round(medium_confidence / total_reqs * 100, 1) if total_reqs > 0 else 0,
        "low_confidence_count": low_confidence,
        "low_confidence_pct": round(low_confidence / total_reqs * 100, 1) if total_reqs > 0 else 0,
        "average_confidence": round(avg_confidence, 3),
    }
    
    # =========================================================================
    # 5. RECOMMENDATIONS
    # =========================================================================
    
    recommendations = []
    
    # Recommendation: Data source mapping
    if data_source_coverage < 80:
        recommendations.append(
            f"Improve data source mapping: {100 - data_source_coverage:.0f}% of requirements need asset linkage. "
            "Review chunking strategy to capture table headers and section context."
        )
    
    # Recommendation: Low confidence review
    if low_confidence > 0:
        recommendations.append(
            f"Manual review recommended for {low_confidence} low-confidence requirements. "
            "These may benefit from additional context or prompt refinement."
        )
    
    # Recommendation: Schema compliance
    if reqs_with_schema_issues > total_reqs * 0.1:
        recommendations.append(
            f"Address schema compliance: {reqs_with_schema_issues} requirements have issues. "
            "Review schema_repair logic or prompt guidance for missing fields."
        )
    
    # Recommendation: Fragment validation
    if fragment_warnings > 0:
        recommendations.append(
            f"Validate {fragment_warnings} fragment warnings. "
            "These requirements may have incomplete context due to chunking boundaries."
        )
    
    # Recommendation: Gate decision
    if gate_decision.get("decision") == "human_review":
        recommendations.append(
            "Gate decision is 'human_review'. Review failing checks before proceeding to Neo4j ingestion."
        )
    
    return InsightsResult(
        quality_assessment=quality_assessment,
        risk_flags=risk_flags,
        rule_type_distribution=rule_type_distribution,
        hallucination_risk=hallucination_risk,
        confidence_distribution=confidence_distribution,
        recommendations=recommendations,
    )


def _get_quality_tier(schema_pct: float, grounding_pct: float, data_source_pct: float) -> str:
    """Determine overall quality tier based on component metrics."""
    avg_score = (schema_pct + grounding_pct + data_source_pct) / 3
    
    if avg_score >= 90:
        return "Excellent"
    elif avg_score >= 75:
        return "Good"
    elif avg_score >= 60:
        return "Fair"
    else:
        return "Needs Review"


def _get_automation_tier(counts: dict[str, int], total: int) -> str:
    """Determine automation readiness tier."""
    if total == 0:
        return "Unknown"
    
    automated_pct = counts["automated"] / total * 100
    
    if automated_pct >= 80:
        return "Highly Automatable"
    elif automated_pct >= 60:
        return "Mostly Automatable"
    elif automated_pct >= 40:
        return "Mixed Automation"
    else:
        return "Requires Manual Effort"


def insights_to_dict(insights: InsightsResult) -> dict[str, Any]:
    """Convert InsightsResult to dictionary for JSON serialization."""
    return {
        "quality_assessment": insights.quality_assessment,
        "risk_flags": insights.risk_flags,
        "rule_type_distribution": insights.rule_type_distribution,
        "hallucination_risk": insights.hallucination_risk,
        "confidence_distribution": insights.confidence_distribution,
        "recommendations": insights.recommendations,
    }
