from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

import pytest

from prompt_registry import PromptRegistry
from rule_agent import RuleAgent, Rule


class FakeLLM:
    def __init__(self, payloads: List[dict[str, Any]]):
        self._payloads = payloads
        self._idx = 0

    def invoke(self, messages):
        if self._idx >= len(self._payloads):
            return json.dumps({"rules": []})
        payload = self._payloads[self._idx]
        self._idx += 1
        return json.dumps(payload)


def test_agent_smoke_extract_rules_from_text() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])

    llm = FakeLLM(
        payloads=[
            {
                "rules": [
                    {
                        "rule_id": "R-DQ-001",
                        "category": "rule",
                        "rule_type": "data_quality_threshold",
                        "rule_description": "Deposit account records must meet minimum 99.5% accuracy standard",
                        "grounded_in": "meeting 99.5% accuracy standards",
                        "confidence": 0.95,
                        "attributes": {
                            "metric": "Data accuracy",
                            "threshold_value": 99.5,
                            "threshold_direction": "minimum",
                        },
                        "metadata": {
                            "source_block": "National Banking Corporation shall maintain deposit account records meeting 99.5% accuracy standards.",
                            "source_location": "lines:1-2",
                        },
                    }
                ]
            }
        ]
    )

    agent = RuleAgent(registry=registry, llm=llm)

    doc = "National Banking Corporation shall maintain deposit account records\nmeeting 99.5% accuracy standards"
    rules = agent.extract_rules(document_text=doc)

    assert len(rules) == 1
    assert isinstance(rules[0], Rule)
    assert rules[0].rule_type.value == "data_quality_threshold"


def test_strict_grounding_drops_ungrounded() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])

    llm = FakeLLM(
        payloads=[
            {
                "rules": [
                    {
                        "rule_id": "R-DQ-001",
                        "category": "rule",
                        "rule_type": "data_quality_threshold",
                        "rule_description": "Ungrounded claim",
                        "grounded_in": "this text is not in the section",
                        "confidence": 0.95,
                        "attributes": {
                            "metric": "Data accuracy",
                            "threshold_value": 99.5,
                            "threshold_direction": "minimum",
                        },
                        "metadata": {
                            "source_block": "some block",
                            "source_location": "lines:1-1",
                        },
                    }
                ]
            }
        ]
    )

    agent = RuleAgent(registry=registry, llm=llm)
    doc = "Only this line exists"
    rules = agent.extract_rules(document_text=doc)
    assert rules == []


def test_agent_smoke_extract_grc_components_from_text() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])

    llm = FakeLLM(
        payloads=[
            {
                "policies": [
                    {
                        "component_type": "policy",
                        "component_id": "P-001",
                        "component_title": "Data Quality and Accuracy Standards",
                        "component_owner": "Chief Compliance Officer",
                        "policy_objective": "Establish enterprise-wide data quality standards",
                        "source_table_identifier": "Table:1",
                        "validation_errors": [],
                        "metadata": {"source_block": "x", "source_location": "lines:1-1"},
                    }
                ],
                "risks": [
                    {
                        "component_type": "risk",
                        "component_id": "R-001",
                        "risk_description": "Inaccurate data may lead to noncompliance.",
                        "risk_owner": "Chief Operations Officer",
                        "source_table_identifier": "Table:2",
                        "validation_errors": [],
                        "metadata": {"source_block": "y", "source_location": "lines:1-1"},
                    }
                ],
                "controls": [
                    {
                        "component_type": "control",
                        "component_id": "C-001",
                        "control_description": "Validate data accuracy on ingest.",
                        "control_owner": "Data Governance Lead",
                        "source_table_identifier": "Table:3",
                        "validation_errors": [],
                        "metadata": {"source_block": "z", "source_location": "lines:1-1"},
                    }
                ],
                "extraction_summary": {"notes": "ok"},
            }
        ]
    )

    agent = RuleAgent(registry=registry, llm=llm)
    doc = "Row 0: Policy ID | P-001\nRow 1: Policy Title | Data Quality and Accuracy Standards"
    components = agent.extract_grc_components(document_text=doc)

    assert "policies" in components
    assert "risks" in components
    assert "controls" in components
    assert len(components["policies"]) == 1
    assert len(components["risks"]) == 1
    assert len(components["controls"]) == 1
    assert components["policies"][0].component_id == "P-001"
    assert components["controls"][0].component_id == "C-001"


@pytest.mark.skipif(True, reason="Requires local FDIC doc file")
def test_agent_with_fdic_docx_path() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])
    llm = FakeLLM(payloads=[{"rules": []}])
    agent = RuleAgent(registry=registry, llm=llm)
    rules = agent.extract_rules(document_path=str(Path("data") / "FDIC_370_GRC_Library_National_Bank.docx"))
    assert rules == []
