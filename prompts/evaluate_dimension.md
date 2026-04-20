# Evaluate Dimension Protocol

Evaluate a single quality dimension using the **tool-first hierarchy** and **MiniMax M2.7 LLM**.

---

## Step 1: Route to Correct LLM

All dimensions use MiniMax M2.7 via OpenClaw:

```bash
python3 scripts/llm_router.py <dimension> [tool_output.txt]
```

---

## Step 2: Run Tools

Run all tools for this dimension. Save raw output:

```bash
# Output path: .sessi-work/round_<n>/tools/<dimension>.txt
```

**Tool commands by dimension:**

| Dimension | Command |
|-----------|---------|
| linting | `pylint --output-format=json --disable=import-error <target>` |
| type_safety | `mypy <target> --output-format=json` |
| test_coverage | `pytest --cov --cov-output=json --cov-report=term:skip` |
| security | `bandit -r -f json <target>` |
| secrets_scanning | `gitleaks detect --report=json` |
| architecture | `cloc --json <target>` + CRG analysis |
| readability | `radon cc -a <target>` |
| error_handling | `grep -r "try:" <target> --include="*.py" \| wc -l` |
| documentation | `grep -r '"""' <target> --include="*.py" \| wc -l` |
| license_compliance | `scancode --output=json <target>` |
| performance | skip |
| mutation_testing | `pytest tests/ --gremlins --gremlins-executor=subprocess -q` |

---

## Step 3: Evaluate with MiniMax M2.7

Use the router prompt:

```bash
python3 scripts/llm_router.py <dimension> .sessi-work/round_<n>/tools/<dimension>.txt
```

**CRG integration (if available):**

```bash
python3 scripts/crg_wrapper.py <cmd> <repo>
```

Available CRG commands: `hub-nodes`, `bridge-nodes`, `communities`, `arch-overview`, `flows`, `dead-code`, `surprising`, `knowledge-gaps`, `stats`

---

## Step 4: Write Score File

Save to `.sessi-work/round_<n>/scores/<dimension>.json`:

```json
{
  "dimension": "<name>",
  "round": <n>,
  "llm_provider": "minimax",
  "tool_score": <0-100>,
  "llm_score": <0-100>,
  "score": <min(tool_score, llm_score)>,
  "findings": [
    {
      "file": "<path|null>",
      "line": <int|null>,
      "severity": "critical|high|medium|low|info",
      "message": "<description>",
      "evidence": "<tool output excerpt or file:line>"
    }
  ],
  "gaps": ["<gap 1>", "<gap 2>"],
  "tool_outputs": "<path to raw tool output>",
  "reconcile": "tool_first"
}
```

---

## Step 5: Register Findings in the Issue Registry

```bash
echo '{"severity":"high","message":"...","file":"src/foo.py","line":42,"evidence":"..."}' \
  > /tmp/finding.json

python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json \
  <dimension> \
  <round_num> \
  /tmp/finding.json
```

---

## Anti-Bias Rules

1. `score = min(tool_score, llm_score)` — no exceptions
2. Every finding needs `evidence` field — no bare assertions
3. Δ > 10 from previous round requires tool evidence or ≥ 3 lines of git diff
