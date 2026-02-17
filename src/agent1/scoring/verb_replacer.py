"""Vague verb replacement for regulatory requirements.

Replaces generic, hard-to-operationalize verbs with specific actionable language
as specified in windsurf_agent_feedback.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Vague verbs and their specific replacements based on context
VAGUE_VERB_MAPPINGS = {
    "ensure": {
        "default": "monitor and verify",
        "threshold": "monitor {metric} and escalate if below {threshold}",
        "data": "reconcile and validate",
        "compliance": "verify compliance with",
    },
    "verify": {
        "default": "sample and compare",
        "accuracy": "sample {n} records and compare to source",
        "completeness": "audit for missing fields",
        "data": "reconcile against source system",
    },
    "validate": {
        "default": "test and confirm",
        "system": "execute test cases and confirm expected behavior",
        "data": "reconcile to authoritative source",
        "process": "audit process steps and document results",
    },
    "review": {
        "default": "audit and document",
        "periodic": "conduct {frequency} audit of",
        "sample": "sample {n} records and audit",
        "approval": "review and sign-off on",
    },
    "maintain": {
        "default": "monitor, track, and report",
        "threshold": "monitor and keep above {threshold}",
        "records": "update and preserve",
        "system": "monitor availability and performance of",
    },
    "confirm": {
        "default": "verify and document",
        "data": "reconcile and obtain written confirmation",
        "approval": "obtain signed approval from",
        "compliance": "audit and certify compliance with",
    },
    "check": {
        "default": "inspect and document",
        "data": "query and validate",
        "system": "test and verify functionality of",
    },
    "manage": {
        "default": "track, monitor, and report on",
        "risk": "identify, assess, and mitigate",
        "process": "execute, monitor, and optimize",
    },
}

# Context keywords for selecting replacement variant
CONTEXT_KEYWORDS = {
    "threshold": ["threshold", "percent", "%", "accuracy", "completeness", "quality"],
    "data": ["data", "record", "field", "value", "information"],
    "compliance": ["compliance", "regulatory", "requirement", "rule", "policy"],
    "system": ["system", "application", "platform", "service", "api"],
    "accuracy": ["accuracy", "accurate", "correct", "error"],
    "completeness": ["complete", "completeness", "missing", "required field"],
    "periodic": ["quarterly", "monthly", "annual", "weekly", "daily"],
    "sample": ["sample", "sampling", "random"],
    "approval": ["approval", "approve", "sign-off", "authorize"],
    "records": ["record", "documentation", "file", "log"],
    "risk": ["risk", "threat", "vulnerability", "exposure"],
    "process": ["process", "procedure", "workflow", "operation"],
}


@dataclass
class VerbReplacementResult:
    """Result of vague verb replacement."""
    original: str
    replaced: str
    replacements_made: list[dict[str, str]]
    has_vague_verbs: bool
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "replaced": self.replaced,
            "replacements_made": self.replacements_made,
            "has_vague_verbs": self.has_vague_verbs,
        }


def _detect_context(text: str) -> str:
    """Detect the context of the text to select appropriate replacement."""
    text_lower = text.lower()
    
    # Score each context
    scores = {}
    for context, keywords in CONTEXT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[context] = score
    
    if not scores:
        return "default"
    
    # Return highest scoring context
    return max(scores, key=scores.get)


def _extract_attributes(text: str) -> dict[str, str]:
    """Extract attribute values from text for template substitution."""
    attrs = {
        "n": "100",  # Default sample size
        "frequency": "quarterly",
        "threshold": "",
        "metric": "",
    }
    
    # Extract threshold value
    threshold_match = re.search(r"(\d+\.?\d*)\s*%", text)
    if threshold_match:
        attrs["threshold"] = f"{threshold_match.group(1)}%"
    
    # Extract frequency
    for freq in ["daily", "weekly", "monthly", "quarterly", "annual"]:
        if freq in text.lower():
            attrs["frequency"] = freq
            break
    
    # Extract metric type
    for metric in ["accuracy", "completeness", "timeliness", "availability"]:
        if metric in text.lower():
            attrs["metric"] = metric
            break
    
    return attrs


def replace_vague_verbs(text: str, attributes: dict[str, Any] = None) -> VerbReplacementResult:
    """
    Replace vague verbs in text with specific actionable language.
    
    Args:
        text: The rule description text
        attributes: Optional requirement attributes for context
    
    Returns:
        VerbReplacementResult with original and replaced text
    """
    if attributes is None:
        attributes = {}
    
    original = text
    replaced = text
    replacements = []
    
    # Detect context
    context = _detect_context(text)
    
    # Extract attributes for template substitution
    template_attrs = _extract_attributes(text)
    template_attrs.update({k: str(v) for k, v in attributes.items() if isinstance(v, (str, int, float))})
    
    # Find and replace vague verbs
    for vague_verb, replacements_map in VAGUE_VERB_MAPPINGS.items():
        # Create pattern to match verb (case-insensitive, word boundary)
        pattern = re.compile(rf"\b({vague_verb}s?|{vague_verb}ing|{vague_verb}ed)\b", re.IGNORECASE)
        
        matches = pattern.findall(replaced)
        if matches:
            # Select replacement based on context
            replacement_template = replacements_map.get(context, replacements_map["default"])
            
            # Substitute template variables
            try:
                replacement = replacement_template.format(**template_attrs)
            except KeyError:
                replacement = replacements_map["default"]
            
            # Preserve original case
            for match in matches:
                if match[0].isupper():
                    replacement_cased = replacement.capitalize()
                else:
                    replacement_cased = replacement
                
                replaced = pattern.sub(replacement_cased, replaced, count=1)
                replacements.append({
                    "original_verb": match,
                    "replacement": replacement_cased,
                    "context": context,
                })
    
    return VerbReplacementResult(
        original=original,
        replaced=replaced,
        replacements_made=replacements,
        has_vague_verbs=len(replacements) > 0,
    )


def has_vague_verbs(text: str) -> bool:
    """Check if text contains vague verbs."""
    text_lower = text.lower()
    for vague_verb in VAGUE_VERB_MAPPINGS:
        if re.search(rf"\b{vague_verb}\b", text_lower):
            return True
    return False


def get_vague_verb_count(text: str) -> int:
    """Count vague verbs in text."""
    text_lower = text.lower()
    count = 0
    for vague_verb in VAGUE_VERB_MAPPINGS:
        count += len(re.findall(rf"\b{vague_verb}\b", text_lower))
    return count
