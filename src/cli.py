from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from agent1.nodes.preprocessor import parse_and_chunk
from agent1.nodes.schema_discovery import schema_discovery_agent
from agent1.nodes.confidence_gate import check_confidence
from agent1.nodes.grc_extractor import GRCComponentExtractorNode
from agent1.nodes.atomizer import RequirementAtomizerNode
from agent1.eval.eval_node import eval_quality


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the main CLI parser with subcommands for Agent1 pipeline."""
    parser = argparse.ArgumentParser(
        prog="kratos-discover",
        description="Kratos Discover Agent - Extract regulatory requirements from documents",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Preprocess command
    preprocess_parser = subparsers.add_parser(
        "preprocess",
        help="Parse DOCX into deterministic chunks (Node 1)",
    )
    preprocess_parser.add_argument(
        "--input",
        dest="input_path",
        required=True,
        help="Path to input document (.docx)",
    )
    preprocess_parser.add_argument(
        "--output",
        dest="output_path",
        default="",
        help="Optional output JSON file path. If not set, writes to outputs/.",
    )
    preprocess_parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=os.getenv("KRATOS_OUTPUT_DIR", "outputs"),
        help="Directory to save outputs when --output is not set.",
    )
    preprocess_parser.add_argument(
        "--max-chunk-chars",
        dest="max_chunk_chars",
        type=int,
        default=3000,
        help="Maximum characters per chunk.",
    )
    preprocess_parser.add_argument(
        "--min-chunk-chars",
        dest="min_chunk_chars",
        type=int,
        default=50,
        help="Minimum characters per chunk (smaller chunks are skipped).",
    )
    preprocess_parser.add_argument(
        "--log-level",
        dest="log_level",
        default=os.getenv("KRATOS_LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    preprocess_parser.add_argument(
        "--dotenv",
        dest="dotenv_path",
        default=".env",
        help="Path to .env file to load (default: .env at repo root)",
    )
    
    # Discover-schema command
    schema_parser = subparsers.add_parser(
        "discover-schema",
        help="Run Schema Discovery Agent (Nodes 1-3)",
    )
    schema_parser.add_argument(
        "--input",
        dest="input_path",
        required=True,
        help="Path to input document (.docx)",
    )
    schema_parser.add_argument(
        "--output",
        dest="output_path",
        default="",
        help="Optional output JSON file path. If not set, writes to outputs/.",
    )
    schema_parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=os.getenv("KRATOS_OUTPUT_DIR", "outputs"),
        help="Directory to save outputs when --output is not set.",
    )
    schema_parser.add_argument(
        "--max-chunks",
        dest="max_chunks",
        type=int,
        default=10,
        help="Maximum number of chunks to send to Claude for discovery.",
    )
    schema_parser.add_argument(
        "--log-level",
        dest="log_level",
        default=os.getenv("KRATOS_LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    schema_parser.add_argument(
        "--dotenv",
        dest="dotenv_path",
        default=".env",
        help="Path to .env file to load (default: .env at repo root)",
    )
    
    # Atomize command (full pipeline)
    atomize_parser = subparsers.add_parser(
        "atomize",
        help="Run full pipeline: preprocess -> schema -> gate -> atomize -> eval (Nodes 1-5)",
    )
    atomize_parser.add_argument(
        "--input",
        dest="input_path",
        required=True,
        help="Path to input document (.docx)",
    )
    atomize_parser.add_argument(
        "--output",
        dest="output_path",
        default="",
        help="Optional output JSON file path. If not set, writes to outputs/.",
    )
    atomize_parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=os.getenv("KRATOS_OUTPUT_DIR", "outputs"),
        help="Directory to save outputs when --output is not set.",
    )
    atomize_parser.add_argument(
        "--log-level",
        dest="log_level",
        default=os.getenv("KRATOS_LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    atomize_parser.add_argument(
        "--dotenv",
        dest="dotenv_path",
        default=".env",
        help="Path to .env file to load (default: .env at repo root)",
    )

    return parser



def run_preprocess(
    input_path: str,
    output_path: str = "",
    output_dir: str = "outputs",
    max_chunk_chars: int = 3000,
    min_chunk_chars: int = 50,
) -> int:
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    input_stem = input_p.stem

    if output_path:
        output_file = Path(output_path)
    else:
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        output_file = out_dir_path / f"preprocess_{input_stem}_{run_id}.json"

    logger.info("[plan] Agent1 Preprocess")
    logger.info("[plan] - Parse DOCX into deterministic chunks")
    logger.info(
        "[run] input=%s output=%s max_chunk_chars=%s min_chunk_chars=%s",
        str(input_p),
        str(output_file),
        max_chunk_chars,
        min_chunk_chars,
    )

    out = parse_and_chunk(
        file_path=input_p,
        file_type="docx",
        max_chunk_chars=max_chunk_chars,
        min_chunk_chars=min_chunk_chars,
    )

    payload = out.model_dump()
    text = json.dumps(payload, indent=2)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text, encoding="utf-8")
    logger.info("[output] wrote=%s", str(output_file))

    return 0


def run_schema_discovery(
    input_path: str,
    output_path: str = "",
    output_dir: str = "outputs",
    max_chunks: int = 10,
) -> int:
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    input_stem = input_p.stem

    if output_path:
        output_file = Path(output_path)
    else:
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        output_file = out_dir_path / f"schema_discovery_{input_stem}_{run_id}.json"

    logger.info("[plan] Schema Discovery Agent (Node 2)")
    logger.info("[plan] - Parse DOCX into chunks")
    logger.info("[plan] - Call Claude to infer document structure")
    logger.info("[plan] - Return SchemaMap with discovered entities and fields")
    logger.info(
        "[run] input=%s output=%s max_chunks=%s",
        str(input_p),
        str(output_file),
        max_chunks,
    )

    # Step 1: Parse document
    preprocessor_output = parse_and_chunk(
        file_path=input_p,
        file_type="docx",
        max_chunk_chars=3000,
        min_chunk_chars=50,
    )
    logger.info("[preprocess] chunks=%s", len(preprocessor_output.chunks))

    # Step 2: Initialize state - pass ALL chunks for stratified sampling
    # The schema discovery agent will do its own stratified sampling
    state = {
        "file_path": str(preprocessor_output.file_path),
        "chunks": preprocessor_output.chunks,  # Pass all chunks for stratified sampling
        "prompt_versions": {},
        "errors": [],
    }

    # Step 3: Run schema discovery
    logger.info("[schema_discovery] calling Claude...")
    result = schema_discovery_agent(state)
    schema_map = result.get("schema_map")

    if schema_map is None:
        logger.error("[schema_discovery] failed to discover schema")
        return 1

    logger.info(
        "[schema_discovery] entities=%s avg_confidence=%.2f%% pattern=%s",
        len(schema_map.entities),
        schema_map.avg_confidence * 100,
        schema_map.structural_pattern,
    )

    # Step 4: Check confidence gate (CF-8: structured decision)
    gate_result = check_confidence(state | {"schema_map": schema_map})
    logger.info("[confidence_gate] decision=%s score=%.3f", gate_result.decision, gate_result.score)

    # Step 5: Save output
    payload = {
        "schema_map": schema_map.model_dump(),
        "gate_decision": gate_result.to_dict(),
        "preprocessor_stats": preprocessor_output.document_stats,
    }
    text = json.dumps(payload, indent=2)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text, encoding="utf-8")
    logger.info("[output] wrote=%s", str(output_file))

    return 0


def run_atomizer(
    input_path: str,
    output_path: str = "",
    output_dir: str = "outputs",
) -> int:
    """Run the full pipeline: preprocess -> schema discovery -> atomizer."""
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    input_stem = input_p.stem

    if output_path:
        output_file = Path(output_path)
    else:
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        output_file = out_dir_path / f"requirements_{input_stem}_{run_id}.json"

    logger.info("[plan] Requirement Atomizer Pipeline (Nodes 1-5)")
    logger.info("[plan] - Node 1: Parse DOCX into chunks")
    logger.info("[plan] - Node 2: Schema Discovery")
    logger.info("[plan] - Node 3: Confidence Gate")
    logger.info("[plan] - Node 3.5: GRC Component Extraction")
    logger.info("[plan] - Node 4: Requirement Atomizer")
    logger.info("[plan] - Node 5: Eval Quality")
    logger.info("[run] input=%s output=%s", str(input_p), str(output_file))

    # Node 1: Parse document
    preprocessor_output = parse_and_chunk(
        file_path=input_p,
        file_type="docx",
        max_chunk_chars=3000,
        min_chunk_chars=50,
    )
    logger.info("[node1] preprocess chunks=%s", len(preprocessor_output.chunks))

    # Node 2: Schema Discovery
    state = {
        "file_path": str(preprocessor_output.file_path),
        "chunks": preprocessor_output.chunks,
        "prompt_versions": {},
        "errors": [],
        "extraction_iteration": 1,
    }

    logger.info("[node2] schema_discovery calling Claude...")
    schema_result = schema_discovery_agent(state)
    schema_map = schema_result.get("schema_map")

    if schema_map is None:
        logger.error("[node2] schema_discovery failed")
        return 1

    logger.info(
        "[node2] schema_discovery entities=%s avg_confidence=%.2f%%",
        len(schema_map.entities),
        schema_map.avg_confidence * 100,
    )

    # Node 3: Confidence Gate (CF-8: structured decision)
    state["schema_map"] = schema_map
    gate_result = check_confidence(state)
    logger.info(
        "[node3] confidence_gate decision=%s score=%.3f",
        gate_result.decision,
        gate_result.score,
    )
    if gate_result.failing_checks:
        logger.warning("[node3] failing_checks=%s", gate_result.failing_checks)
    if gate_result.conditional_flags:
        logger.info("[node3] conditional_flags=%s", gate_result.conditional_flags)

    if gate_result.decision == "reject":
        logger.error("[node3] confidence_gate rejected: %s", gate_result.rationale)
        return 1

    # Node 3.5: GRC Component Extraction
    logger.info("[node3.5] grc_extractor calling Claude...")
    grc_extractor = GRCComponentExtractorNode()
    grc_result = grc_extractor(state)
    grc_components = grc_result.get("grc_components")
    state["grc_components"] = grc_components
    state["component_index"] = grc_result.get("component_index", {})

    if grc_components:
        logger.info(
            "[node3.5] grc_extractor policies=%s risks=%s controls=%s",
            len(grc_components.policies),
            len(grc_components.risks),
            len(grc_components.controls),
        )
    else:
        logger.warning("[node3.5] grc_extractor returned no components")

    # Node 4: Requirement Atomizer
    logger.info("[node4] atomizer calling Claude...")
    atomizer = RequirementAtomizerNode()
    atomizer_result = atomizer(state)

    requirements = atomizer_result.get("requirements", [])
    extraction_metadata = atomizer_result.get("extraction_metadata")

    logger.info(
        "[node4] atomizer extracted=%s requirements avg_confidence=%.2f%%",
        len(requirements),
        extraction_metadata.avg_confidence * 100 if extraction_metadata else 0,
    )

    # Node 5: Eval Quality
    state["requirements"] = requirements
    state["extraction_metadata"] = extraction_metadata
    state["prompt_versions"] = atomizer_result.get("prompt_versions", {})
    
    logger.info("[node5] eval_quality running checks...")
    eval_result = eval_quality(state)
    eval_report = eval_result.get("eval_report", {})
    
    logger.info(
        "[node5] eval_quality failure_type=%s severity=%s quality_score=%.2f%%",
        eval_report.get("failure_type", "none"),
        eval_report.get("failure_severity", "low"),
        eval_report.get("overall_quality_score", 0) * 100,
    )

    # Save output
    payload = {
        "requirements": [r.model_dump() for r in requirements],
        "extraction_metadata": extraction_metadata.model_dump() if extraction_metadata else {},
        "grc_components": grc_components.model_dump() if grc_components else {},
        "eval_report": eval_report,
        "schema_map": schema_map.model_dump(),
        "gate_decision": gate_result.to_dict(),  # CF-8: Structured decision
        "preprocessor_stats": preprocessor_output.document_stats,
    }
    text = json.dumps(payload, indent=2)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(text, encoding="utf-8")
    logger.info("[output] wrote=%s", str(output_file))

    return 0


def _setup_logging(log_level: str) -> None:
    """Configure logging with reduced noise from HTTP libraries."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    _setup_logging(args.log_level)
    load_dotenv(args.dotenv_path)

    if args.command == "preprocess":
        return run_preprocess(
            input_path=args.input_path,
            output_path=args.output_path,
            output_dir=args.output_dir,
            max_chunk_chars=args.max_chunk_chars,
            min_chunk_chars=args.min_chunk_chars,
        )

    if args.command == "discover-schema":
        return run_schema_discovery(
            input_path=args.input_path,
            output_path=args.output_path,
            output_dir=args.output_dir,
            max_chunks=args.max_chunks,
        )

    if args.command == "atomize":
        return run_atomizer(
            input_path=args.input_path,
            output_path=args.output_path,
            output_dir=args.output_dir,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
