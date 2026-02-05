from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from prompt_registry import PromptRegistry
from rule_agent import RuleAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rule-agent", description="Run the LangGraph Rule Agent")

    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default=os.getenv("LLM_PROVIDER", "openai"),
        help="LLM provider",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=os.getenv("FDIC_370_PATH", "rule-agent/data/FDIC_370_GRC_Library_National_Bank.docx"),
        help="Path to FDIC document (.docx/.pdf/.html)",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="",
        help="Optional output JSON file path. If not set, prints to stdout.",
    )
    parser.add_argument(
        "--prompt-version",
        dest="prompt_version",
        default="",
        help="Override active prompt version for rule_extraction (e.g., v1.0)",
    )
    parser.add_argument(
        "--dotenv",
        dest="dotenv_path",
        default=".env",
        help="Path to .env file to load (default: .env at repo root)",
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
    input_path: str,
    output_path: str = "",
    prompt_version: str = "",
    base_dir: Optional[Path] = None,
) -> int:
    base_dir = base_dir or Path(__file__).resolve().parent
    registry = PromptRegistry(base_dir=base_dir)

    if prompt_version:
        registry.set_active_version("rule_extraction", prompt_version)

    llm = _build_llm(provider)
    agent = RuleAgent(registry=registry, llm=llm)

    rules = agent.extract_rules(document_path=input_path)
    payload = {"rules": [r.model_dump() for r in rules]}

    text = json.dumps(payload, indent=2)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_dotenv(args.dotenv_path)

    return run(
        provider=args.provider,
        input_path=args.input_path,
        output_path=args.output_path,
        prompt_version=args.prompt_version,
        base_dir=Path(__file__).resolve().parent,
    )


if __name__ == "__main__":
    raise SystemExit(main())
