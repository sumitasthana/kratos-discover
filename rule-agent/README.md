# rule-agent

Production-grade Rule Agent built with LangGraph.

## What it does
- Segments the FDIC 370 source document into extractable sections.
- Extracts Rules (including controls and risks) using Claude + JSON output.
- Validates, deduplicates, and enforces strict grounding against the FDIC source.

## Data source
Place the FDIC source file here (gitignored):
- `rule-agent/data/FDIC_370_GRC_Library_National_Bank.docx`

## Setup
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r rule-agent/requirements.txt
```

Create env file:
- Copy `rule-agent/config/.env.example` to `.env` (repo root) or set env vars in your shell.

## Running (example)
```python
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

registry = PromptRegistry(base_dir=Path("rule-agent"))
llm = ChatAnthropic(
    model=os.getenv("CLAUDE_MODEL", "claude-opus-4-20250805"),
    max_tokens=3000,
    temperature=0,
)

agent = RuleAgent(
    registry=registry,
    llm=llm,
)

rules = agent.extract_rules(document_path=os.getenv("FDIC_370_PATH"))
print(len(rules))
```

## Prompt versioning
- Versioned prompt specs live at `rule-agent/prompts/rule_extraction/vX.Y.yaml`.
- Active version is controlled by `rule-agent/prompts/registry.yaml`.

## Strict grounding
The final grounding node drops any extracted item that cannot be verified against the source section text.
