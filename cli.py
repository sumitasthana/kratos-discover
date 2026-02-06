from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from prompt_registry import PromptRegistry
from rule_agent import RuleAgent


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rule-agent", description="Run the LangGraph Rule Agent")

    parser.add_argument(
        "--mode",
        choices=["rules", "grc_components"],
        default=os.getenv("RULE_AGENT_MODE", "rules"),
        help="Extraction mode: 'rules' (rule_extraction) or 'grc_components' (policies/risks/controls)",
    )

    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default=os.getenv("LLM_PROVIDER", "openai"),
        help="LLM provider",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=os.getenv("FDIC_370_PATH", "data/FDIC_370_GRC_Library_National_Bank.docx"),
        help="Path to FDIC document (.docx/.pdf/.html)",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="",
        help="Optional output JSON file path. If not set, prints to stdout.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=os.getenv("RULE_AGENT_OUTPUT_DIR", "outputs"),
        help="Directory to save outputs (default: outputs/) when --output is not set.",
    )
    parser.add_argument(
        "--prompt-version",
        dest="prompt_version",
        default="",
        help="Override active prompt version for the prompt used by --mode (e.g., v1.0 or v1.2)",
    )
    parser.add_argument(
        "--dotenv",
        dest="dotenv_path",
        default=".env",
        help="Path to .env file to load (default: .env at repo root)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print intermediate pipeline counts.",
    )

    parser.add_argument(
        "--dump-debug",
        action="store_true",
        help="Write debug JSON artifacts into a per-run subfolder (use with --debug).",
    )

    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=os.getenv("RULE_AGENT_LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    return parser


def _build_llm(provider: str) -> Any:
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=0)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = os.getenv("CLAUDE_MODEL", "claude-opus-4-20250805")
        return ChatAnthropic(model=model, max_tokens=3000, temperature=0)

    raise ValueError(f"Unsupported provider: {provider}")


def run(
    provider: str,
    mode: str,
    input_path: str,
    output_path: str = "",
    output_dir: str = "outputs",
    prompt_version: str = "",
    base_dir: Optional[Path] = None,
    debug: bool = False,
    dump_debug: bool = False,
) -> int:
    base_dir = base_dir or Path(__file__).resolve().parent
    registry = PromptRegistry(base_dir=base_dir)

    prompt_name = "rule_extraction" if mode == "rules" else "grc_component_extraction"

    if prompt_version:
        registry.set_active_version(prompt_name, prompt_version)

    llm = _build_llm(provider)
    agent = RuleAgent(registry=registry, llm=llm)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    input_stem = Path(input_path).stem if input_path else "document"

    # If output_path is not explicitly provided, always save a uniquely named file into output_dir.
    # This makes each run traceable and avoids overwriting.
    if output_path:
        output_file = Path(output_path)
    else:
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)

        prefix = "rules" if mode == "rules" else "grc_components"
        output_file = out_dir_path / f"{prefix}_{input_stem}_{provider}_{run_id}.json"

    logger.info("[plan] Rule Agent Run")
    logger.info("[plan] - mode=%s", mode)
    logger.info("[plan] - Load prompt spec (%s) and render system prompt", prompt_name)
    logger.info("[plan] - Segment document into sections")
    logger.info("[plan] - Extract with LLM (structured output when available)")
    logger.info("[plan] - Validate/parse and apply strict grounding")
    logger.info("[plan] - Write JSON output")
    logger.info(
        "[run] provider=%s mode=%s input=%s output=%s debug=%s",
        provider,
        mode,
        input_path,
        str(output_file),
        debug,
    )

    if debug:
        state: dict[str, Any] = {"document_path": input_path}

        state = agent._segment_requirements_node(state)  # type: ignore[attr-defined]
        sections = state.get("sections", [])
        logger.info("[segment] sections=%s", len(sections))

        if mode == "rules":
            state = agent._extract_rules_node(state)  # type: ignore[attr-defined]
            raw_rules = state.get("raw_rules", [])
            logger.info("[extract] raw_rules=%s", len(raw_rules))

            state = agent._validate_parse_node(state)  # type: ignore[attr-defined]
            validated = state.get("validated_rules", [])
            logger.info("[validate] validated_rules=%s", len(validated))

            state = agent._deduplication_node(state)  # type: ignore[attr-defined]
            deduped = state.get("deduplicated_rules", [])
            logger.info("[deduplicate] deduplicated_rules=%s", len(deduped))

            state = agent._grounding_scoring_node(state)  # type: ignore[attr-defined]
            final_rules = state.get("final_rules", [])
            logger.info("[ground] final_rules=%s", len(final_rules))

            if dump_debug:
                debug_dir = output_file.resolve().parent / f"debug_{run_id}"
                debug_dir.mkdir(parents=True, exist_ok=True)
                (debug_dir / "raw_rules.json").write_text(
                    json.dumps({"rules": raw_rules}, indent=2),
                    encoding="utf-8",
                )
                (debug_dir / "validated_rules.json").write_text(
                    json.dumps({"rules": validated}, indent=2),
                    encoding="utf-8",
                )
                (debug_dir / "deduped_rules.json").write_text(
                    json.dumps({"rules": deduped}, indent=2),
                    encoding="utf-8",
                )
                logger.info("[debug] wrote=%s", str(debug_dir))

            payload = {"rules": [r.model_dump() for r in final_rules]}
        else:
            state = agent._extract_grc_components_node(state)  # type: ignore[attr-defined]
            raw_components = state.get("raw_components", {})
            logger.info(
                "[extract] raw_components policies=%s risks=%s controls=%s",
                len(list(raw_components.get("policies", []))),
                len(list(raw_components.get("risks", []))),
                len(list(raw_components.get("controls", []))),
            )

            state = agent._validate_grc_components_node(state)  # type: ignore[attr-defined]
            validated_components = state.get("validated_components", {})
            logger.info(
                "[validate] validated_components policies=%s risks=%s controls=%s",
                len(list(validated_components.get("policies", []))),
                len(list(validated_components.get("risks", []))),
                len(list(validated_components.get("controls", []))),
            )

            state = agent._ground_grc_components_node(state)  # type: ignore[attr-defined]
            final_components = state.get("final_components", {})
            logger.info(
                "[ground] final_components policies=%s risks=%s controls=%s",
                len(list(final_components.get("policies", []))),
                len(list(final_components.get("risks", []))),
                len(list(final_components.get("controls", []))),
            )

            if dump_debug:
                debug_dir = output_file.resolve().parent / f"debug_{run_id}"
                debug_dir.mkdir(parents=True, exist_ok=True)

                validated_dump = {
                    "policies": [getattr(p, "model_dump", lambda: p)() for p in validated_components.get("policies", [])],
                    "risks": [getattr(r, "model_dump", lambda: r)() for r in validated_components.get("risks", [])],
                    "controls": [getattr(c, "model_dump", lambda: c)() for c in validated_components.get("controls", [])],
                    "extraction_summary": dict(validated_components.get("extraction_summary", {})),
                }
                (debug_dir / "raw_components.json").write_text(
                    json.dumps(raw_components, indent=2),
                    encoding="utf-8",
                )
                (debug_dir / "validated_components.json").write_text(
                    json.dumps(validated_dump, indent=2),
                    encoding="utf-8",
                )
                logger.info("[debug] wrote=%s", str(debug_dir))

            payload = {
                "policies": [p.model_dump() for p in final_components.get("policies", [])],
                "risks": [r.model_dump() for r in final_components.get("risks", [])],
                "controls": [c.model_dump() for c in final_components.get("controls", [])],
                "extraction_summary": dict(final_components.get("extraction_summary", {})),
            }
    else:
        if mode == "rules":
            rules = agent.extract_rules(document_path=input_path)
            payload = {"rules": [r.model_dump() for r in rules]}
        else:
            components = agent.extract_grc_components(document_path=input_path)
            payload = {
                "policies": [p.model_dump() for p in components.get("policies", [])],
                "risks": [r.model_dump() for r in components.get("risks", [])],
                "controls": [c.model_dump() for c in components.get("controls", [])],
                "extraction_summary": dict(components.get("extraction_summary", {})),
            }

    text = json.dumps(payload, indent=2)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text, encoding="utf-8")
    logger.info("[output] wrote=%s", str(output_file))

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    # Reduce noisy transport logs; keep app milestone logs readable.
    # Users can still raise verbosity with --log-level DEBUG.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    load_dotenv(args.dotenv_path)

    return run(
        provider=args.provider,
        mode=args.mode,
        input_path=args.input_path,
        output_path=args.output_path,
        output_dir=args.output_dir,
        prompt_version=args.prompt_version,
        base_dir=Path(__file__).resolve().parent,
        debug=bool(args.debug),
        dump_debug=bool(args.dump_debug),
    )


if __name__ == "__main__":
    raise SystemExit(main())
