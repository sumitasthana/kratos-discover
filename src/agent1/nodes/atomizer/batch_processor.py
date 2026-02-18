"""Batch processing utilities for the Requirement Atomizer.

Handles LLM calls with retries, batch building, and token tracking.
"""
from __future__ import annotations

import time
from typing import Any

import structlog

from agent1.models.chunks import ContentChunk
from agent1.models.requirements import ChunkSkipReason, RegulatoryRequirement
from agent1.models.schema_map import SchemaMap
from agent1.nodes.atomizer.prompt_builder import PromptBuilder
from agent1.nodes.atomizer.response_parser import ResponseParser
from agent1.utils.llm_client import get_anthropic_client

logger = structlog.get_logger(__name__)

# Configuration constants
MAX_BATCH_CHARS = 12000  # Target 80% of context window
MAX_RETRIES_PER_BATCH = 3
RETRY_BACKOFF_BASE = 2.0


class BatchProcessor:
    """Processes batches of chunks through the LLM."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()

    def build_batches(self, chunks: list[ContentChunk]) -> list[list[ContentChunk]]:
        """Group chunks into batches that fit within context window."""
        batches: list[list[ContentChunk]] = []
        current_batch: list[ContentChunk] = []
        current_chars = 0

        # Group by entity type when possible
        entity_chunks: dict[str, list[ContentChunk]] = {}
        other_chunks: list[ContentChunk] = []

        for chunk in chunks:
            entity_type = chunk.annotations.get("record_type")
            if entity_type:
                entity_chunks.setdefault(entity_type, []).append(chunk)
            else:
                other_chunks.append(chunk)

        # Process entity-grouped chunks first
        all_ordered: list[ContentChunk] = []
        for entity_type in sorted(entity_chunks.keys()):
            all_ordered.extend(entity_chunks[entity_type])
        all_ordered.extend(other_chunks)

        for chunk in all_ordered:
            chunk_chars = chunk.char_count

            # If single chunk exceeds budget, process alone
            if chunk_chars > MAX_BATCH_CHARS:
                if current_batch:
                    batches.append(current_batch)
                batches.append([chunk])
                current_batch = []
                current_chars = 0
                continue

            # Check if adding this chunk exceeds budget
            if current_chars + chunk_chars > MAX_BATCH_CHARS:
                if current_batch:
                    batches.append(current_batch)
                    # Overlap: include last chunk of previous batch
                    current_batch = [current_batch[-1], chunk]
                    current_chars = current_batch[0].char_count + chunk_chars
                else:
                    current_batch = [chunk]
                    current_chars = chunk_chars
            else:
                current_batch.append(chunk)
                current_chars += chunk_chars

        if current_batch:
            batches.append(current_batch)

        return batches

    def process_batch(
        self,
        batch: list[ContentChunk],
        schema_map: SchemaMap,
        prompt_config: dict,
        prompt_version: str,
        extraction_iteration: int,
    ) -> tuple[list[RegulatoryRequirement], int, int, ChunkSkipReason | None]:
        """Process a single batch of chunks through the LLM.
        
        Returns: (requirements, input_tokens, output_tokens, skip_reason)
        skip_reason is None if requirements were extracted, otherwise indicates why not.
        """
        # Build prompts
        schema_context = self.prompt_builder.build_schema_context(schema_map)
        chunks_content = self.prompt_builder.build_chunks_content(batch)
        system_prompt = self.prompt_builder.build_system_prompt(prompt_config, schema_context)
        user_message = self.prompt_builder.build_user_message(prompt_config, chunks_content)

        # Set temperature based on iteration
        temperature = 0.0 if extraction_iteration == 2 else 0.1

        # Create client using shared factory
        client = get_anthropic_client()

        last_error = None
        for attempt in range(MAX_RETRIES_PER_BATCH):
            try:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                # Extract token usage
                input_tokens = response.usage.input_tokens if response.usage else 0
                output_tokens = response.usage.output_tokens if response.usage else 0

                # Parse response
                content = response.content[0].text if response.content else "[]"
                
                # Detect empty response
                if not content or content.strip() in ("[]", "null", ""):
                    return [], input_tokens, output_tokens, ChunkSkipReason.EMPTY_RESPONSE
                
                requirements, parse_error = self.response_parser.parse_response_with_status(
                    content=content,
                    batch=batch,
                    schema_version=schema_map.schema_version,
                    prompt_version=prompt_version,
                    extraction_iteration=extraction_iteration,
                )
                
                # Determine skip reason
                if not requirements:
                    if parse_error:
                        return [], input_tokens, output_tokens, ChunkSkipReason.PARSE_ERROR
                    else:
                        return [], input_tokens, output_tokens, ChunkSkipReason.NO_EXTRACTABLE_CONTENT

                return requirements, input_tokens, output_tokens, None

            except Exception as e:
                last_error = e
                logger.warning(
                    "atomizer_llm_retry",
                    attempt=attempt,
                    error=str(e),
                )
                time.sleep(RETRY_BACKOFF_BASE ** attempt)

        raise last_error or RuntimeError("LLM call failed")
