# kratos-discover

Production-grade Rule Agent built with LangGraph.

## What it does
- Segments the FDIC 370 source document into extractable sections.
- Extracts Rules (including controls and risks) using an LLM with schema-based structured output when supported (falls back to JSON parsing).
- Validates, deduplicates, and enforces strict grounding against the FDIC source.

## Data source
Place the FDIC source file here (gitignored):
- `data/FDIC_370_GRC_Library_National_Bank.docx`

## Setup
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Create env file:
- Copy `config/.env.example` to `.env` (repo root) or set env vars in your shell.

## Running (example)
```python
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from rule_agent import RuleAgent
from prompt_registry import PromptRegistry

registry = PromptRegistry(base_dir=Path("."))

# Option A: Anthropic
llm = ChatAnthropic(model=os.getenv("CLAUDE_MODEL", "claude-opus-4-20250805"), max_tokens=3000, temperature=0)

# Option B: OpenAI
# llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)

agent = RuleAgent(
    registry=registry,
    llm=llm,
)

rules = agent.extract_rules(document_path=os.getenv("FDIC_370_PATH"))
print(len(rules))
```

## Running (CLI)
From the repo root:

```bash
python cli.py --provider openai --input data/FDIC_370_GRC_Library_National_Bank.docx --output out.json
```

Use Anthropic:

```bash
python cli.py --provider anthropic --input data/FDIC_370_GRC_Library_National_Bank.docx --output out.json
```

Override the active prompt version:

```bash
python cli.py --provider openai --prompt-version v1.0 --output out.json
```

## Prompt versioning
- Versioned prompt specs live at `prompts/rule_extraction/vX.Y.yaml`.
- Active version is controlled by `prompts/registry.yaml`.

## Strict grounding
The final grounding node drops any extracted item that cannot be verified against the source section text.
