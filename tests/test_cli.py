from __future__ import annotations

from pathlib import Path

from docx import Document

from rule_agent import RuleAgent
from agent1.nodes.preprocessor import parse_and_chunk


def test_imports() -> None:
    # Smoke test that modules are importable.
    assert RuleAgent is not None


def test_cli_parser_builds() -> None:
    from cli import build_parser

    parser = build_parser()
    args = parser.parse_args([])

    assert args.mode in {"rules", "grc_components"}
    assert args.provider in {"openai", "anthropic"}
    assert isinstance(args.input_path, str)
    assert isinstance(args.output_dir, str)
    assert isinstance(args.log_level, str)
    assert hasattr(args, "dump_debug")


def test_cli_preprocess_writes_output(tmp_path: Path) -> None:
    from cli import main

    input_docx = tmp_path / "sample.docx"
    doc = Document()
    doc.add_heading("H1", level=1)
    doc.add_paragraph("Hello world")
    doc.save(str(input_docx))

    out_path = tmp_path / "out.json"
    code = main(
        [
            "preprocess",
            "--input",
            str(input_docx),
            "--output",
            str(out_path),
            "--min-chunk-chars",
            "1",
        ]
    )

    assert code == 0
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").strip().startswith("{")
