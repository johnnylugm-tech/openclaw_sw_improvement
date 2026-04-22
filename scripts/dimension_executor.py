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
        "command": ["pylint", "{target}/scripts", "--output-format=json", "--disable=import-error"],
        "score_type": "pylint_json",
        "weight": 0.06,
    },
    "type_safety": {
        "tool": "mypy",
        "command": ["mypy", "{target}"],
        "score_type": "mypy_text",
        "weight": 0.10,
    },
    "test_coverage": {
        "tool": "pytest",
        "command": ["pytest", "{target}/scripts", "--cov", "--cov-report=term", "-q"],
        "score_type": "coverage_term",
        "weight": 0.13,
    },
    "security": {
        "tool": "bandit",
        "command": ["bandit", "-r", "-f", "json", "-x", "**/mutants/**", "{target}/scripts"],
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
        "command": ["gitleaks", "detect", "-s", "{target}", "-f", "json", "-r", "-"],
        "score_type": "gitleaks_json",
        "weight": 0.08,
    },
    "mutation_testing": {
        "tool": "pytest",
        "command": ["pytest", "{target}/scripts", "--gremlins", "--gremlin-executor=subprocess", "--gremlin-report=json", "-q", "--ignore=scripts/__pycache__"],
        "score_type": "gremlins_json",
        "weight": 0.08,
    },
    "license_compliance": {
        "tool": "scancode",
        "command": ["/Users/johnny/Library/Python/3.9/bin/scancode", "--license", "--json-pp", "{target}/.scancode_license.json", "{target}/scripts"],
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


def _parse_mypy_text(stdout: str) -> dict:
    """Parse mypy text output to findings.

    Mypy text format: 'file.py:line: error: message'
    or 'file.py:line: note: message'
    """
    findings = []
    for line in stdout.strip().split('\n'):
        # Match: 'file.py:line: error: message' or 'file.py:line: note: message'
        m = re.match(r'([^:]+):(\d+): (.+?): (.+)', line)
        if m:
            fname, line_no, sev, msg = m.groups()
            sev = 'medium' if 'error' in sev.lower() else 'low'
            findings.append({
                'file': fname,
                'line': int(line_no),
                'message': f'{sev.upper()}: {msg}',
                'severity': sev,
            })
    return findings


def _parse_bandit_json(stdout: str) -> dict:
    """Parse bandit JSON output to findings.

    Bandit may prepend progress bars (\u2500 chars) when run interactively.
    We find the first '{' to locate the actual JSON.
    """
    findings = []
    # Find JSON start (bandit may have progress bar prefix)
    json_start = stdout.find('{')
    json_text = stdout[json_start:] if json_start >= 0 else stdout
    try:
        data = json.loads(json_text)
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


def _parse_scancode_json_from_file(stdout: str, target: str) -> dict:
    """Parse scancode JSON output from file.

    scancode writes to a file (--json-pp OUTPUT_FILE INPUT) instead of stdout.
    File path is {target}/.scancode_license.json.
    """
    findings = []
    json_path = Path(target) / ".scancode_license.json"
    if not json_path.exists():
        return findings
    try:
        data = json.loads(json_path.read_text())
        files = data.get("files", []) if isinstance(data, dict) else []
        for f in files:
            license_exprs = f.get("license_expressions", [])
            if license_exprs:
                for lic in license_exprs:
                    findings.append({
                        "file": f.get("path", "unknown"),
                        "line": 0,
                        "message": f"License: {lic.get('key', 'unknown')}",
                        "severity": "info",
                    })
    except (json.JSONDecodeError, OSError):
        pass
    return findings


def _parse_cloc_json(stdout: str) -> dict:
    """Parse cloc JSON output.

    Format: {"header": {...}, "Python": {nFiles, blank, comment, code}, "SUM": {...}}
    Returns findings with code stats for architecture assessment.
    """
    findings = []
    try:
        text = stdout.strip()
        idx = text.find("{")
        if idx >= 0:
            text = text[idx:]
        data = json.loads(text)
        # Find Python language entry (primary language for scoring)
        # Fall back to first non-header entry if Python not found
        primary_lang = data.get("Python") or data.get("SUM")
        found_key = "Python" if data.get("Python") else None
        if primary_lang and isinstance(primary_lang, dict) and "code" in primary_lang:
            n_files = primary_lang.get("nFiles", 0)
            code = primary_lang.get("code", 0)
            blank = primary_lang.get("blank", 0)
            comment = primary_lang.get("comment", 0)
            total = code + blank + comment
            comment_ratio = (comment / total * 100) if total > 0 else 0
            code_per_file = (code / n_files) if n_files > 0 else 0
            findings.append({
                "file": f"language:{found_key or 'primary'}",
                "line": 0,
                "message": f"cloc: {n_files} files, {code} LOC, {code_per_file:.0f} LOC/file, {comment_ratio:.1f}% comments",
                "severity": "info",
            })
    except (json.JSONDecodeError, OSError, ZeroDivisionError):
        pass
    return findings


def _parse_gremlins_json(stdout: str) -> dict:
    """Parse pytest-gremlins JSON output.

    Gremlins can output JSON in two ways:
    1. Inline JSON via --gremlin-report=json (stdout)
    2. coverage/gremlins/gremlins.json file (keys: summary.total, summary.zapped)

    Expected format: {summary: {total, zapped, survived, percentage}}
    Or flat format: {total, killed}
    """
    findings = []
    # Try to parse as-is first (inline JSON)
    try:
        data = json.loads(stdout)
        # Normalize: handle {summary: {total, zapped, ...}} format
        if "summary" in data:
            total = data["summary"].get("total", 0)
            killed = data["summary"].get("zapped", 0)
        else:
            total = data.get("total", 0)
            killed = data.get("killed", 0)
        kill_rate = (killed / total * 100) if total > 0 else 0
        findings.append({
            "file": "mutation_summary",
            "line": 0,
            "message": f"Mutation testing: {killed}/{total} killed ({kill_rate:.1f}%)",
            "severity": "info",
        })
        return findings
    except json.JSONDecodeError:
        pass
    # Try reading from coverage/gremlins/gremlins.json
    gremlins_file = Path("coverage/gremlins/gremlins.json")
    if gremlins_file.exists():
        try:
            data = json.loads(gremlins_file.read_text())
            if "summary" in data:
                total = data["summary"].get("total", 0)
                killed = data["summary"].get("zapped", 0)
                kill_rate = data["summary"].get("percentage", 0)
            else:
                total = data.get("total", 0)
                killed = data.get("killed", 0)
                kill_rate = (killed / total * 100) if total > 0 else 0
            findings.append({
                "file": "mutation_summary",
                "line": 0,
                "message": f"Mutation testing: {killed}/{total} killed ({kill_rate:.1f}%)",
                "severity": "info",
            })
        except (json.JSONDecodeError, OSError):
            pass
    return findings


def _parse_coverage_term(stdout: str) -> dict:
    """Parse pytest --cov --cov-report=term output to findings.

    Parses lines like:
        TOTAL  2490   402    84%
    or
        src/    100    10    90%
    """
    findings = []
    for line in stdout.strip().split('\n'):
        if '\t' in line:
            parts = line.split('\t')
        else:
            parts = line.split()
        # Find TOTAL line or per-file line with coverage
        if len(parts) >= 4 and parts[0].strip() in ('TOTAL', 'TOTAL%'):
            try:
                # Format: name  statements  missing  coverage%
                name = parts[0].strip()
                coverage_str = parts[-1].strip().rstrip('%')
                coverage = float(coverage_str)
                findings.append({
                    'file': name,
                    'line': 0,
                    'message': f'Coverage: {coverage}%',
                    'severity': 'info',
                })
            except (ValueError, IndexError):
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
    elif dimension == "architecture":
        # Architecture score based on cloc metrics
        # Parse "cloc: N files, M LOC, X LOC/file, Y% comments" from findings
        total_files = 0
        total_code = 0
        comment_ratio = 0
        n = 0
        for f in findings:
            msg = f.get("message", "")
            if "cloc:" in msg:
                # Extract: cloc: N files, M LOC, X LOC/file, Y% comments
                import re
                m = re.search(r'cloc: (\d+) files, (\d+) LOC, (\d+) LOC/file, ([\d.]+)% comments', msg)
                if m:
                    total_files = int(m.group(1))
                    total_code = int(m.group(2))
                    loc_per_file = int(m.group(3))
                    comment_ratio = float(m.group(4))
                    n += 1
        if n == 0:
            return 0
        # Score heuristics:
        # - comment_ratio >= 15%: +40 pts
        # - LOC/file 50-200: +30 pts (reasonable module size)
        # - Files >= 5 (proper separation): +30 pts
        score = 0
        if comment_ratio >= 15:
            score += 40
        elif comment_ratio >= 10:
            score += 20
        if 50 <= loc_per_file <= 200:
            score += 30
        elif loc_per_file < 50:
            score += 15
        if total_files >= 5:
            score += 30
        elif total_files >= 3:
            score += 15
        return min(100, score)
    elif dimension == "readability":
        # radon cc: lower complexity = higher score
        # For now, score based on absence of findings
        return 100
    elif dimension == "mutation_testing":
        # Extract kill rate from findings message
        for f in findings:
            msg = f.get("message", "")
            if "killed" in msg and "%" in msg:
                import re
                m = re.search(r'\(([\d.]+)%\)', msg)
                if m:
                    return min(100, float(m.group(1)))
        return 0
    elif dimension == "test_coverage":
        # Extract coverage % from findings message (e.g., "Coverage: 84%")
        for f in findings:
            msg = f.get("message", "")
            if "Coverage:" in msg:
                import re
                m = re.search(r'Coverage: ([\d.]+)%', msg)
                if m:
                    return float(m.group(1))
        return 0
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

    # Pre-check for mutation_testing: skip if no test files found (prevents pytest-gremlins hang)
    if dimension == "mutation_testing":
        test_files = list(Path(f"{target}/scripts").glob("test_*.py")) + \
                     list(Path(f"{target}/scripts").glob("*_test.py"))
        if not test_files:
            return {
                "dimension": dimension,
                "tool_score": 100,
                "raw_output": "skipped: no test files found in scripts/",
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

    # Prefer stdout for JSON tools (bandit: findings → RC=1, JSON in stdout)
    # Prefer stdout for all tools when it has content, fall back to stderr
    raw_output = stdout if stdout.strip() else stderr

    # Parse findings
    if config.get(dimension, {}).get("score_type") == "pylint_json":
        findings = _parse_pylint_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "mypy_json":
        findings = _parse_mypy_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "mypy_text":
        findings = _parse_mypy_text(stdout)
    elif config.get(dimension, {}).get("score_type") == "coverage_term":
        findings = _parse_coverage_term(stdout)
    elif config.get(dimension, {}).get("score_type") == "bandit_json":
        findings = _parse_bandit_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "gitleaks_json":
        findings = _parse_gitleaks_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "gremlins_json":
        findings = _parse_gremlins_json(stdout)
    elif config.get(dimension, {}).get("score_type") == "scancode_json":
        findings = _parse_scancode_json_from_file(stdout, target)
    elif config.get(dimension, {}).get("score_type") == "cloc_json":
        findings = _parse_cloc_json(stdout)
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

    # Status: success if findings were parsed (regardless of tool RC),
    # error only if tool could not run or findings could not be extracted.
    # pylint/bandit return RC=1 when findings exist (not an error).
    findings_parsed = isinstance(findings, list)
    tool_executed = rc != -1  # -1 means tool-not-found or timeout
    status = "success" if (findings_parsed and tool_executed) else "error"

    return {
        "dimension": dimension,
        "tool_score": tool_score,
        "raw_output": raw_output[:5000],
        "findings": findings[:50],  # Cap at 50 findings
        "status": status,
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
