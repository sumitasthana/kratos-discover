"""Pipeline runner utilities for CLI commands.

Provides common orchestration patterns for the various CLI run_* functions
to reduce code duplication.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Common pipeline orchestration utilities."""
    
    def __init__(
        self,
        input_path: str,
        output_path: str = "",
        output_dir: str = "outputs",
        output_prefix: str = "output",
    ):
        self.input_path = Path(input_path)
        self.output_dir = output_dir
        self.output_prefix = output_prefix
        
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Generate run ID
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        
        # Determine output file
        if output_path:
            self.output_file = Path(output_path)
        else:
            out_dir_path = Path(output_dir)
            out_dir_path.mkdir(parents=True, exist_ok=True)
            self.output_file = out_dir_path / f"{output_prefix}_{self.input_path.stem}_{self.run_id}.json"
    
    def log_plan(self, steps: list[str]) -> None:
        """Log the pipeline plan."""
        logger.info("[plan] %s", steps[0] if steps else "Pipeline")
        for step in steps[1:]:
            logger.info("[plan] - %s", step)
    
    def log_run(self, **kwargs) -> None:
        """Log run parameters."""
        params = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info("[run] input=%s output=%s %s", str(self.input_path), str(self.output_file), params)
    
    def log_step(self, step_name: str, **kwargs) -> None:
        """Log a pipeline step with optional metrics."""
        if kwargs:
            metrics = " ".join(f"{k}={v}" for k, v in kwargs.items())
            logger.info("[%s] %s", step_name, metrics)
        else:
            logger.info("[%s] started", step_name)
    
    def log_error(self, step_name: str, message: str) -> None:
        """Log an error."""
        logger.error("[%s] %s", step_name, message)
    
    def write_output(self, payload: dict[str, Any]) -> None:
        """Write output to JSON file."""
        text = json.dumps(payload, indent=2)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(text, encoding="utf-8")
        logger.info("[output] wrote=%s", str(self.output_file))
    
    def run_with_steps(
        self,
        steps: list[tuple[str, Callable[[], Any]]],
        on_error: Optional[Callable[[str, Exception], int]] = None,
    ) -> tuple[dict[str, Any], int]:
        """Run a sequence of named steps.
        
        Args:
            steps: List of (step_name, step_function) tuples
            on_error: Optional error handler returning exit code
            
        Returns:
            (results_dict, exit_code)
        """
        results: dict[str, Any] = {}
        
        for step_name, step_fn in steps:
            try:
                self.log_step(step_name)
                result = step_fn()
                results[step_name] = result
            except Exception as e:
                self.log_error(step_name, str(e))
                if on_error:
                    return results, on_error(step_name, e)
                return results, 1
        
        return results, 0


def create_runner(
    input_path: str,
    output_path: str = "",
    output_dir: str = "outputs",
    output_prefix: str = "output",
) -> PipelineRunner:
    """Factory function to create a PipelineRunner."""
    return PipelineRunner(
        input_path=input_path,
        output_path=output_path,
        output_dir=output_dir,
        output_prefix=output_prefix,
    )
