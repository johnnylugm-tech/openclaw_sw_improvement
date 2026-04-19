#!/opt/homebrew/bin/python3.12
"""
LLM Router: Unified MiniMax M2.7 routing for all dimension evaluations.

Removes Gemini/Claude tier routing — all evaluations use MiniMax M2.7.
"""

import os
import sys
import json

_MINIMAX_MODEL = os.environ.get("HARNESS_MODEL", "minimax/MiniMax-M2.7")

ALL_DIMENSIONS = [
    "linting", "type_safety", "test_coverage", "security", "performance",
    "architecture", "readability", "error_handling", "documentation",
    "secrets_scanning", "mutation_testing", "license_compliance",
    "property_testing", "fuzzing", "accessibility", "observability",
    "supply_chain_security",
]

PROMPT_TEMPLATE = """\
You are a code quality evaluator. Analyze the following tool output for the '{dimension}' dimension and return a JSON evaluation.

## Tool Output
{tool_output}

## Code Context (if provided)
{code_sample}

## Task
1. Score the dimension 0-100 based ONLY on the tool output evidence
2. List up to 5 concrete findings with line references where available
3. Identify the top gap to fix

Return ONLY valid JSON in this exact format:
{{
  "dimension": "{dimension}",
  "tool_score": <0-100>,
  "llm_score": <0-100>,
  "score": <min of tool_score and llm_score>,
  "findings": [
    {{"line": <int or null>, "severity": "critical|warning|info", "message": "<text>", "evidence": "<tool output excerpt>"}}
  ],
  "gaps": ["<top gap 1>", "<top gap 2>"],
  "tool_outputs": "<raw tool output summary>",
  "reconcile": "tool_first"
}}
"""


def route(dimension: str) -> dict:
    """Return routing decision for a dimension (all use MiniMax M2.7)."""
    return {
        "dimension": dimension,
        "model": _MINIMAX_MODEL,
        "provider": "minimax",
        "token_budget": {"input": 20000, "output": 4000},
        "rationale": "All dimensions use MiniMax M2.7 via OpenClaw",
    }


def build_prompt(dimension: str, tool_output: str, code_sample: str = "") -> str:
    """Build evaluation prompt for a dimension."""
    return PROMPT_TEMPLATE.format(
        dimension=dimension,
        tool_output=tool_output[:6000],
        code_sample=code_sample[:2000] if code_sample else "(not provided)",
    )


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dimension> [tool_output_file]")
        sys.exit(1)
    dimension = sys.argv[1]
    tool_output = ""
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            tool_output = f.read()
    decision = route(dimension)
    decision["prompt"] = build_prompt(dimension, tool_output)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
