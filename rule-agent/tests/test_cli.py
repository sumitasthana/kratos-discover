from __future__ import annotations

from rule_agent import RuleAgent


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
