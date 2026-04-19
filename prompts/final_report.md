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
