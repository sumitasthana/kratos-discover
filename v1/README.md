# v1 Plan / Working Notes

## Purpose
This folder (v1/) is the working area for building a LangGraph-based extraction agent that produces grounded Rules (including controls and risks) from a single authoritative source document:

- FDIC_370_GRC_Library_National_Bank

## Key Decisions (Confirmed)
- Working directory: all dev work lives under v1/.
- Grounding policy: Strict mode.
  - If an extracted item cannot be supported with evidence from the FDIC 370 source document, it must be dropped/rejected.
- PromptRegistry behavior: Option B.
  - register_version() writes the prompt spec file and updates the registry manifest.
- Prompt version format: versioned .yaml prompt specs (not .txt).
  - Example reference: v1/agent-discover-prompt-v1.0.yaml.
- Single output model: everything is a Rule.
  - We use a required `category` field: `rule | control | risk`.
  - `rule_type` remains a closed enum for sub-types.

## Source Document (FDIC 370 Library)
- Location in repo: v1/data/
- Primary format: .docx
- Also support (minimum viable): .pdf, .html

### Grounding Requirements
Every output Rule must include:
- grounded_in: exact or near-exact excerpt from the FDIC 370 text.
- metadata.source_block: a verbatim quote block (or contiguous excerpt) from FDIC 370.
- metadata.source_location: a stable reference produced by ingestion, e.g.:
  - DOCX: heading path + paragraph index (and optionally table/row identifiers)
  - PDF: page number + line/section hint (best-effort)
  - HTML: URL/filename + element path/id

Validation must reject rules if:
- Evidence text is missing
- Source location is missing
- Evidence cannot be traced to the FDIC 370 chunks used during processing

## Prompting Strategy (YAML Prompt Specs)
Prompts are authored as structured YAML specs (see agent-discover-prompt-v1.0.yaml) with:
- role
- rule_types (machine-readable taxonomy)
- output_schema (fixed keys; category codes; confidence calibration)
- instructions
- anti_patterns
- user_message_template (inject block header/content)

### Prompt Versioning Layout (v1)
Proposed:
- v1/prompts/registry.yaml
- v1/prompts/rule_extraction/v1.0.yaml
- v1/prompts/rule_extraction/v1.1.yaml
- ...

registry.yaml maps prompt name -> active version -> version metadata -> file path.

## PromptRegistry (Option B) - Planned Responsibilities
- Read/write v1/prompts/registry.yaml
- Load a versioned prompt spec YAML from v1/prompts/<prompt_name>/<version>.yaml
- Provide:
  - get_prompt(prompt_name, version)
  - get_active_prompt(prompt_name)
  - list_versions(prompt_name)
  - set_active_version(prompt_name, version)
  - register_version(prompt_name, version, spec: dict, created_by="") (writes YAML + updates manifest)

## LangGraph Agent (High-Level)
Linear graph (no branching initially):
- segment -> extract -> validate/parse -> deduplicate -> ground/score

### Node Responsibilities (Strict Grounding)
- Segment:
 - Ingest FDIC doc into blocks/chunks with stable source_location.
- Extract:
 - Use active prompt spec from PromptRegistry.
 - Provide the block header/content via the prompt's user_message_template.
  - LLM returns JSON {"rules": [...]}.
- Validate & Parse:
 - Enforce schema and types.
 - Enforce rule_type membership in the allowed enum.
 - Enforce confidence range.
 - Enforce presence of evidence fields.
- Deduplicate:
 - Merge duplicates based on normalized rule_description + source_location + type.
- Ground & Score:
 - Verify grounded_in/source_block matches the chunk text.
 - Reject anything that cannot be matched to FDIC blocks.

## Rule Types (Taxonomy Expansion Plan)
Current example prompt (agent-discover-prompt-v1.0.yaml) defines 6 types.
We will extend rule_type (still a closed enum) to cover:
- Controls (e.g., control requirements, monitoring, testing, governance)
- Risks (e.g., data quality risk, operational risk, compliance risk)

Implementation approach:
- Update the prompt spec rule_types section to include additional types with:
 - required/optional attributes
 - examples
- Update category codes mapping accordingly.

## Milestones (Implementation Order)
1. Create .gitignore (ignore document-misc/).
2. Establish v1/ prompt registry scaffolding (manifest + loader).
3. Create FDIC ingestion utilities (DOCX first; PDF/HTML best-effort).
4. Build LangGraph pipeline with strict grounding enforcement.
5. Expand prompt taxonomy for controls/risks and add tests.

## Notes
- document-misc/ is intentionally ignored by git and treated as scratch/reference.
