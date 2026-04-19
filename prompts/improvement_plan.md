# Improvement Plan Protocol (Issue-Driven)

Plan and execute fixes for **open issues in the registry**, not just failing dimensions.

---

## Step 1: Load Open Issues + Verified Scores

```bash
# Saturation check
python3 scripts/issue_tracker.py saturation \
  .sessi-work/issue_registry.json <current_round>

# Verified scores
python3 scripts/score.py .sessi-work/round_<n> config.json \
  .sessi-work/issue_registry.json > .sessi-work/round_<n>/final_score.json

# Open-issue queue
python3 scripts/issue_tracker.py open .sessi-work/issue_registry.json \
  > .sessi-work/round_<n>/open_issues.json
```

---

## Step 2: Prioritize Fixes (Severity-First)

Priority order:
```
1. ALL open critical issues      → MUST fix
2. ALL open high issues          → MUST fix
3. Open medium in failing dims   → fix if time allows
4. Open medium in passing dims   → fix only if no 1/2/3 work remains
5. Open low / info               → batch fix or defer with reason
```

### Cost-Benefit Triage

Apply `wontfix` ONLY when ALL four conditions hold:

| Condition | Evaluate |
|-----------|----------|
| severity | `low` or `info` |
| occurrence probability | extremely low |
| impact if triggered | negligible |
| fix cost / risk | high |

Register the decision:
```bash
python3 scripts/issue_tracker.py wontfix \
  .sessi-work/issue_registry.json <issue_id> <round> \
  "<4-part structured reason>"
```

### Per-dimension fix strategy and caps

| Dimension | Fix Strategy | Max fixes/round |
|-----------|-------------|-----------------|
| linting | Automated (run `--fix` flag) | Unlimited |
| type_safety | Add type hints | 5 |
| test_coverage | Add targeted tests | 3 |
| security | Apply remediation | 3 |
| secrets_scanning | Remove/rotate | All (zero tolerance) |
| architecture | Refactor carefully | 1-2 |
| readability | Rename + extract | 3 |
| error_handling | Add exception handlers | 5 |
| documentation | Add docstrings | 5 |

**Guardrails (never do):**
- Do NOT remove test assertions
- Do NOT broaden `except Exception` → bare `except:`
- Do NOT add `@ts-ignore`, `# type: ignore`, `# noqa`

---

## Step 3: Per-Issue Fix + Verification Loop

For each open issue:
1. Apply fix (minimal, targeted change)
2. Re-run dimension tool
3. Decide outcome:
   - IF improvement and no regression → git commit, `issue_tracker.py fix`
   - IF no improvement → defer, `issue_tracker.py defer <id> <round> "<reason>"`
   - IF intentionally rejected → wontfix, `issue_tracker.py wontfix <id> <round> "<reason>"`

---

## Step 4: Deferred / Wontfix Issues

```bash
python3 scripts/issue_tracker.py defer \
  .sessi-work/issue_registry.json <id> <round> \
  "Requires architectural decision beyond automated scope"

python3 scripts/issue_tracker.py wontfix \
  .sessi-work/issue_registry.json <id> <round> \
  "Tool false positive: <tool> flags X but see <file:line>"
```

---

## Output

```bash
python3 scripts/checkpoint.py round <n> scores.json <overall_score>
python3 scripts/issue_tracker.py summary .sessi-work/issue_registry.json
```
