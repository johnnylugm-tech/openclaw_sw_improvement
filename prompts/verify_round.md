# Verify Round Protocol

Cross-check all dimension scores after improvements. Detect regressions and cap unsupported claims.

---

## Step 1: Run Deterministic Verification

```bash
python3 scripts/verify.py \
  .sessi-work/round_<n>/result.json \
  .sessi-work/round_<n> \
  <repo_path>
```

Read:
- `verification.capped[]` — dimensions where claims were capped
- `verification.regressions[]` — dimensions that got worse
- `verified: true/false` — overall pass/fail

**Use `verified.json` for all downstream steps.**

---

## Step 1a: Structural Verification (CRG, if available)

Refresh the graph and measure structural drift vs previous round:

```bash
# Refresh graph after all round commits
code-review-graph update --repo <target>

# Get previous round tag
PREV_TAG=$(git tag -l "round-*" | sort -V | tail -1)

# Measure drift vs previous round
git rev-parse "$PREV_TAG" > /dev/null 2>&1 && \
  code-review-graph detect-changes --base "$PREV_TAG" --repo <target> || \
  echo "No previous round tag found"
```

**Decision rules:**
- `risk_score >= 0.4` → **trigger revert protocol** (structural drift too high)
- New untested functions detected → auto-register as `test_coverage` issues in registry
- `risk_score < 0.4` → proceed normally

**Escalation:**
- Architectural drift → new hub nodes → register as `architecture` issues
- Test gap expansion → missing tests → register as `test_coverage` issues

---

## Step 2: Handle Capped Dimensions

For each entry in `capped[]`:
- Accept the capped score (lower value)
- Log: "Score capped from {claim} to {capped_to}: insufficient evidence"

---

## Step 3: Handle Regressions

For each entry in `regressions[]`:
1. Identify which fix caused the regression
2. IF fix is identifiable AND revert is safe: `git revert <commit_hash> --no-edit`
3. IF regression is acceptable trade-off: document in deferred_fixes.md

---

## Step 4: Final Round Score

```bash
python3 scripts/score.py .sessi-work/round_<n> config.json \
  > .sessi-work/round_<n>/final_score.json
```

Check `meets_target`:
- `true` → trigger early-stop check
- `false` → continue to next round

---

## Output Files

```
.sessi-work/round_<n>/
├── result.json          ← raw (do not use downstream)
├── verified.json        ← verified scores (use this)
├── final_score.json     ← post-verification overall score
└── deferred_fixes.md    ← items requiring human attention
```
