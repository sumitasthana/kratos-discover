from pathlib import Path

import pytest

from prompt_registry import PromptRegistry


def test_get_active_prompt_loads_and_renders() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])
    prompt = registry.get_active_prompt("rule_extraction")

    assert prompt["version"]
    assert "content" in prompt
    assert isinstance(prompt["content"], str)
    assert "You are a regulatory compliance analyst" in prompt["content"]


def test_list_versions() -> None:
    registry = PromptRegistry(base_dir=Path(__file__).resolve().parents[1])
    versions = registry.list_versions("rule_extraction")
    assert "v1.0" in versions


def test_set_active_version_roundtrip(tmp_path: Path) -> None:
    # Copy prompts folder into a temp base_dir to avoid mutating repo.
    base_dir = tmp_path / "rule-agent"
    base_dir.mkdir(parents=True, exist_ok=True)

    src_prompts = Path(__file__).resolve().parents[1] / "prompts"
    dst_prompts = base_dir / "prompts"

    (dst_prompts / "rule_extraction").mkdir(parents=True, exist_ok=True)

    (dst_prompts / "registry.yaml").write_text(
        (src_prompts / "registry.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (dst_prompts / "rule_extraction" / "v1.0.yaml").write_text(
        (src_prompts / "rule_extraction" / "v1.0.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    registry = PromptRegistry(base_dir=base_dir)
    registry.set_active_version("rule_extraction", "v1.0")
    active = registry.get_active_prompt("rule_extraction")
    assert active["version"] == "v1.0"

    with pytest.raises(KeyError):
        registry.set_active_version("rule_extraction", "v9.9")
