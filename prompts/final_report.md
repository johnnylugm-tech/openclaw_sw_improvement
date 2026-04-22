# Final Report Protocol

Generate the end-of-run Quality Improvement Report.

---

## Step 1: Auto-generate Structured Report

```bash
python3 scripts/report_gen.py \
  <repo_path> \
  .sessi-work \
  .sessi-work/issue_registry.json \
  <score_gate> \
  .sessi-work/final_report.md
```

Output sections (all mandatory):
1. Header + Recommendation
2. Summary Statistics
3. Score Trajectory
4. Per-Dimension Breakdown
5. Issues Fixed (with commit SHA + files)
6. Accepted Risks (wontfix + deferred with reasons)
7. Still Open
8. Evidence Trail (git log)

---

## Step 2: Verify Traceability

Every `fixed` issue must have either `commit_sha` or `files_changed`:

```bash
python3 -c "
import json
r = json.load(open('.sessi-work/issue_registry.json'))
for i in r['issues']:
    if i['status'] == 'fixed' and not (i.get('commit_sha') or i.get('files_changed')):
        print(f'MISSING TRACEABILITY: {i[\"id\"]} {i[\"dimension\"]} {i[\"message\"]}')
"
```

---

## Anti-Hallucination Rules

The report is **fact-bound to the registry and git log**. Do not:
- Invent commit SHAs
- Claim files were changed that git does not show
- Change the recommendation from what `report_gen.py` computed
- Silently omit any `accepted_risks` or `open` issue

---

## Sections 8-10 — Narrative（LLM 追加，不覆蓋機器生成）

Read the "Issues Fixed" table. Group fixes by underlying cause, not by dimension.
Surface the 2–4 themes that dominated this run.

Example:
- Missing input validation at API boundaries caused 4 of 7 security findings
- Bare except: idiom from legacy code drove 3 error_handling issues

Summarize the accepted risks by theme. Explain what a future iteration should
re-examine when context changes (e.g. new compliance requirement, new scale).

Explain the state-machine decision from report_gen.py:
- pass — all issues fully resolved
- pass-with-risks — all critical/high/medium fixed; accepted risks remain with reasons
- partial — open medium+ issues remain (max_rounds hit before completion)
- fail — regression or baseline drop detected

One paragraph. Cite the counts (e.g. "5 fixed, 2 wontfix, 0 open medium+").


Sections 8-10 reference Sections 1-7 by ID. They add interpretation, not facts.
