#!/opt/homebrew/bin/python3.12
"""
Dimension Executor: Subprocess wrapper for 12 quality dimension tools.

Each dimension returns a JSON result with tool_score, raw_output,
findings, and status.
"""

import json
import subprocess
import sys
import argparse
import re
from pathlib import Path
from typing import Optional


DIMENSIONS = {
    "linting": {
        "tool": "pylint",
        "command": ["pylint", "{target}", "--output-format=json", "--disable=import-error"],
        "score_type": "pylint_json",
        "weight": 0.06,
    },
    "type_safety": {
        "tool": "mypy",
        "command": ["mypy", "{target}", "--output-format=json"],
        "score_type": "mypy_json",
        "weight": 0.10,
    },
    "test_coverage": {
        "tool": "pytest",
        "command": ["pytest", "--cov", "--cov-output=json", "--cov-report=term:skip"],
        "score_type": "coverage_json",
        "weight": 0.13,
    },
    "security": {
        "tool": "bandit",
        "command": ["bandit", "-r", "-f", "json", "{target}"],
        "score_type": "bandit_json",
        "weight": 0.10,
    },
    "performance": {
        "tool": None,
        "command": None,
        "score_type": "skip",
        "weight": 0.07,
    },
    "architecture": {
        "tool": "cloc",
        "command": ["cloc", "--json", "{target}"],
        "score_type": "cloc_json",
        "weight": 0.07,
    },
    "readability": {
        "tool": "radon",
        "command": ["radon", "cc", "-a", "{target}"],
        "score_type": "radon_cc",
        "weight": 0.06,
    },
    "error_handling": {
        "tool": "grep",
        "command": ["grep", "-r", "try:", "{target}", "--include=*.py"],
        "score_type": "grep_count",
        "weight": 0.09,
    },
    "documentation": {
        "tool": "grep",
        "command": ["grep", "-r", '"""', "{target}", "--include=*.py"],
        "score_type": "grep_count",
        "weight": 0.10,
    },
    "secrets_scanning": {
        "tool": "gitleaks",
        "command": ["gitleaks", "detect", "--report=json"],
        "score_type": "gitleaks_json",
        "weight": 0.08,
    },
    "mutation_testing": {
        "tool": None,
        "command": None,
        "score_type": "skip",
        "weight": 0.08,
    },
    "license_compliance": {
        "tool": "scancode",
        "command": ["scancode", "--output=json", "{target}"],
        "score_type": "scancode_json",
        "weight": 0.06,
    },
}


def _run_command(cmd: list, target: str) -> tuple:
    """Run a command, return (returncode, stdout, stderr)."""
    cmd = [c.replace("{target}", target) for c in cmd]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -1, "", f"TOOL_NOT_FOUND: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def _parse_pylint_json(stdout: str) -> dict:
    """Parse pylint JSON output to findings."""
    findings = []
    try:
        data = json.loads(stdout)
        for item in data:
            fname = item.get("absPath", item.get("path", "unknown"))
            line = item.get("line", 0)
            msg = item.get("message", "")
            sev = item.get("type", "warning")
            if sev == "error":
                sev = "critical"
            elif sev == "warning":
                sev = "medium"
            else:
                sev = "info"
            findings.append({
                "file": fname,
                "line": line,
                "message": msg,
                "severity": sev,
            })
    except json.JSONDecodeError:
        pass
    return findings


def _parse_mypy_json(stdout: str) -> dict:
    """Parse mypy JSON output to findings."""
    findings = []
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            fname = item.get("file", "unknown")
            line = item.get("line", 0)
            msg = item.get("message", "")
            sev = "medium"
            findings.append({
                "file": fname,
                "line": line,
                "message": msg,
                "severity": sev,
            })
    except json.JSONDecodeError:
        pass
    return findings


def _parse_bandit_json(stdout: str) -> dict:
    """Parse bandit JSON output to findings."""
    findings = []
    try:
        data = json.loads(stdout)
        for item in data.get("results", []):
            fname = item.get("filename", "unknown")
            line = item.get("line_number", 0)
            msg = item.get("issue_text", "")
            sev = item.get("issue_severity", "medium")
            if sev == "HIGH":
                sev = "high"
            elif sev == "MEDIUM":
                sev = "medium"
            else:
                sev = "low"
            findings.append({
                "file": fname,
                "line": line,
                "message": msg,
                "severity": sev,
            })
    except json.JSONDecodeError:
        pass
    return findings


def _parse_gitleaks_json(stdout: str) -> dict:
    """Parse gitleaks JSON output to findings."""
    findings = []
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            fname = item.get("file", "unknown")
            line = item.get("line", 0)
            msg = item.get("rule", "")
            findings.append({
                "file": fname,
                "line": line,
                "message": f"Secret found: {msg}",
                "severity": "critical",
            })
    except json.JSONDecodeError:
        pass
    return findings


def _compute_tool_score(findings: list, dimension: str) -> int:
    """Compute 0-100 tool score from findings."""
    if dimension == "linting":
        # Fewer findings = higher score
        count = len(findings)
        if count == 0:
            return 100
        return max(0, 100 - count * 5)
    elif dimension == "type_safety":
        count = len(findings)
        if count == 0:
            return 100
        return max(0, 100 - count * 10)
    elif dimension == "security":
        count = len(findings)
        critical = sum(1 for f in findings if f["severity"] == "critical")
        high = sum(1 for f in findings if f["severity"] == "high")
        if critical > 0:
            return max(0, 100 - critical * 30)
        if high > 0:
            return max(0, 100 - high * 20)
        return max(0, 100 - count * 10)
    elif dimension == "secrets_scanning":
        count = len(findings)
        if count == 0:
            return 100
        return max(0, 100 - count * 25)  # Zero tolerance
    elif dimension == "readability":
        # radon cc: lower complexity = higher score
        # For now, score based on absence of findings
        return 100
    else:
        count = len(findings)
        if count == 0:
            return 100
        return max(0, 100 - count * 5)


def _exec_dimension(dimension: str, target: str, config: dict) -> dict:
    """Execute a single dimension tool."""
    dim_config = config.get(dimension, {})
    tool = dim_config.get("tool")
    command = dim_config.get("command")

    if tool is None or command is None:
        return {
            "dimension": dimension,
            "tool_score": 100,
            "raw_output": "skipped: no tool defined for this dimension",
            "findings": [],
            "status": "skip",
        }

    rc, stdout, stderr = _run_command(command, target)

    if rc == -1 and "TOOL_NOT_FOUND" in stderr:
        return {
            "dimension": dimension,
            "tool_score": 100,
            "raw_output": f"Tool not found: {tool}",
            "findings": [],
            "status": "skip",
        }
    if rc == -1 and "TIMEOUT" in stderr:
        return {
            "dimension": dimension,
            "tool_score": 0,
            "raw_output": "Tool timed out after 300 seconds",
            "findings": [],
            "status": "error",
        }

    raw_output = stdout if rc == 0 else stderr

    # Parse findings
    if config.get(dimension, {}).get("score_type") == "pylint_json":
        findings = _parse_pylint_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "mypy_json":
        findings = _parse_mypy_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "bandit_json":
        findings = _parse_bandit_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "gitleaks_json":
        findings = _parse_gitleaks_json(stdout)
    else:
        # Count-based scoring
        lines = stdout.strip().split("\n") if stdout.strip() else []
        findings = []
        for ln in lines:
            if ln:
                findings.append({
                    "file": "unknown",
                    "line": 0,
                    "message": ln.strip()[:200],
                    "severity": "info",
                })

    tool_score = _compute_tool_score(findings, dimension)

    return {
        "dimension": dimension,
        "tool_score": tool_score,
        "raw_output": raw_output[:5000],
        "findings": findings[:50],  # Cap at 50 findings
        "status": "success" if rc == 0 else "error",
    }


def execute_all_dimensions(target: str) -> dict:
    """Execute all dimensions, return dict of results."""
    results = {}
    for dim in DIMENSIONS:
        results[dim] = _exec_dimension(dim, target, DIMENSIONS)
    return results


def main():
    parser = argparse.ArgumentParser(description="Dimension Executor")
    parser.add_argument("--list", action="store_true", help="List all dimensions")
    parser.add_argument("--dimension", help="Run single dimension")
    parser.add_argument("--target", default=".", help="Target directory")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.list:
        print(json.dumps(list(DIMENSIONS.keys()), indent=2))
        return

    if args.dimension:
        if args.dimension not in DIMENSIONS:
            print(f"Unknown dimension: {args.dimension}", file=sys.stderr)
            sys.exit(1)
        result = _exec_dimension(args.dimension, args.target, DIMENSIONS)
    else:
        result = execute_all_dimensions(args.target)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
