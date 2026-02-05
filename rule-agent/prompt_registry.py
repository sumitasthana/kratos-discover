from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass(frozen=True)
class PromptVersion:
    version: str
    created_at: str
    created_by: str
    file_path: str
    content: str
    spec: Dict[str, Any]


class PromptRegistry:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent
        self._prompts_dir = self._base_dir / "prompts"
        self._registry_path = self._prompts_dir / "registry.yaml"

    def get_prompt(self, prompt_name: str, version: str) -> Dict[str, Any]:
        registry = self._load_registry()
        entry = self._get_prompt_entry(registry, prompt_name)

        versions = entry.get("versions", {})
        if version not in versions:
            raise KeyError(f"Unknown version '{version}' for prompt '{prompt_name}'.")

        info = versions[version]
        spec_path = self._resolve_path(info["file_path"])
        spec = self._load_yaml(spec_path)
        content = self._render_prompt_spec(spec)

        pv = PromptVersion(
            version=version,
            created_at=str(info.get("created_at", "")),
            created_by=str(info.get("created_by", "")),
            file_path=str(info.get("file_path", "")),
            content=content,
            spec=spec,
        )
        return {
            "version": pv.version,
            "created_at": pv.created_at,
            "created_by": pv.created_by,
            "file_path": pv.file_path,
            "content": pv.content,
            "spec": pv.spec,
        }

    def get_active_prompt(self, prompt_name: str) -> Dict[str, Any]:
        registry = self._load_registry()
        entry = self._get_prompt_entry(registry, prompt_name)

        active_version = entry.get("active")
        if not active_version:
            raise KeyError(f"No active version configured for prompt '{prompt_name}'.")

        return self.get_prompt(prompt_name, str(active_version))

    def list_versions(self, prompt_name: str) -> List[str]:
        registry = self._load_registry()
        entry = self._get_prompt_entry(registry, prompt_name)
        versions = entry.get("versions", {})
        return sorted(list(versions.keys()))

    def set_active_version(self, prompt_name: str, version: str) -> None:
        registry = self._load_registry()
        entry = self._get_prompt_entry(registry, prompt_name)

        versions = entry.get("versions", {})
        if version not in versions:
            raise KeyError(f"Unknown version '{version}' for prompt '{prompt_name}'.")

        entry["active"] = version
        self._write_registry(registry)

    def register_version(
        self,
        prompt_name: str,
        version: str,
        spec: Dict[str, Any],
        created_by: str = "",
        make_active: bool = False,
    ) -> None:
        registry = self._load_registry(create_if_missing=True)
        entry = registry.setdefault(prompt_name, {"active": "", "versions": {}})
        versions = entry.setdefault("versions", {})

        prompt_dir = self._prompts_dir / prompt_name
        prompt_dir.mkdir(parents=True, exist_ok=True)

        file_path = f"rule-agent/prompts/{prompt_name}/{version}.yaml"
        spec_path = self._resolve_path(file_path)
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_yaml(spec_path, spec)

        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        versions[version] = {
            "created_at": now,
            "created_by": created_by,
            "file_path": file_path,
        }

        if make_active or not entry.get("active"):
            entry["active"] = version

        self._write_registry(registry)

    def get_version_info(self, prompt_name: str, version: str) -> Dict[str, Any]:
        registry = self._load_registry()
        entry = self._get_prompt_entry(registry, prompt_name)
        versions = entry.get("versions", {})
        if version not in versions:
            raise KeyError(f"Unknown version '{version}' for prompt '{prompt_name}'.")
        return dict(versions[version])

    def _get_prompt_entry(self, registry: Dict[str, Any], prompt_name: str) -> Dict[str, Any]:
        if prompt_name not in registry:
            raise KeyError(f"Unknown prompt '{prompt_name}'.")
        entry = registry[prompt_name]
        if not isinstance(entry, dict):
            raise TypeError(f"Invalid registry entry for prompt '{prompt_name}'.")
        return entry

    def _load_registry(self, create_if_missing: bool = False) -> Dict[str, Any]:
        if not self._registry_path.exists():
            if create_if_missing:
                self._registry_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_registry({})
            else:
                raise FileNotFoundError(f"Registry manifest not found: {self._registry_path}")

        data = self._load_yaml(self._registry_path)
        if not isinstance(data, dict):
            raise TypeError("Registry YAML must be a mapping.")
        return data

    def _write_registry(self, registry: Dict[str, Any]) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_yaml(self._registry_path, registry)

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p

        repo_root = self._base_dir.parent
        return (repo_root / p).resolve()

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise TypeError(f"YAML at {path} must be a mapping.")
        return data

    def _write_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def _render_prompt_spec(self, spec: Dict[str, Any]) -> str:
        role = str(spec.get("role", "")).strip()
        rule_types = spec.get("rule_types", {})
        output_schema = spec.get("output_schema", {})
        instructions = str(spec.get("instructions", "")).strip()
        anti_patterns = spec.get("anti_patterns", [])

        parts: List[str] = []
        if role:
            parts.append(role)

        parts.append("\nRULE TYPES (closed enum):")
        if isinstance(rule_types, dict) and rule_types:
            for name, info in rule_types.items():
                desc = ""
                if isinstance(info, dict):
                    desc = str(info.get("description", "")).strip()
                if desc:
                    parts.append(f"- {name}: {desc}")
                else:
                    parts.append(f"- {name}")
        else:
            parts.append("- (none)")

        parts.append("\nOUTPUT SCHEMA:")
        parts.append(yaml.safe_dump(output_schema, sort_keys=False, allow_unicode=True).strip())

        if instructions:
            parts.append("\nINSTRUCTIONS:\n" + instructions)

        if anti_patterns:
            parts.append("\nANTI-PATTERNS:")
            if isinstance(anti_patterns, list):
                for ap in anti_patterns:
                    parts.append(f"- {ap}")

        return "\n".join(parts).strip() + "\n"
