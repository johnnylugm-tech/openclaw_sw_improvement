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

### 3a. Pre-Fix Safety Gate (CRG Blast Radius)

**Run before every fix.** If the change touches a hub/bridge node or has high risk_score, defer instead of committing blindly.

```bash
# Blast radius of the current uncommitted changes vs HEAD
code-review-graph detect-changes --base HEAD 2>/dev/null || true
```

**Decision rules:**
- `risk_score >= 0.7` → **defer** (too risky to auto-commit)
- Fix touches a hub node or bridge node → **defer** (high blast radius)
- Fix is safe → proceed to Step 3b

> If CRG is not available (`crg_status.json` shows `available: false`),
> skip this gate and rely on the dimension tool re-run verification only.

### 3b. Apply Fix

Apply fix (minimal, targeted change).

### 3c. Post-Fix Verification

1. Re-run dimension tool to confirm improvement
2. Run `code-review-graph detect-changes --base round-<n>` to confirm no blast regression
3. Decide outcome:
   - IF improvement and no regression → git commit, `issue_tracker.py fix <id> <round> "<sha>"`
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
