# SKILL.md — OpenClaw SW Improvement Framework

## Metadata

- **name**: openclaw_sw_improvement
- **description**: Automated software quality improvement via structured tool evaluation, issue tracking, and CRG-powered structural analysis loops
- **trigger phrases**:
  - "run quality loop"
  - "improve code quality"
  - "quality improvement"
  - "software improvement"
  - "start quality analysis"
  - "run sw improvement"
  - "quality scan"
  - "軟體品質提升"
  - "SW improvement"
- **source**: `~/.openclaw/workspace/software_self_improvement/` (local workspace path)

---

## 對話式互動（核心設計）

**人類不需要任何 command line 操作。** 人類只說要做什麼，Agent 讀這份文件後自動執行所有步驟，最後回報結果。

### 觸發範例

```
Human: "run quality improvement on https://github.com/user/repo"
Human: "analyze code quality for my project"
Human: "SW improvement /path/to/my/project"
Human: "軟體品質提升"
```

### Agent 執行流程（內部自動執行）

```
1. 讀取 SKILL.md（就是這份文件）
2. 執行 quality_loop.py init <target_repo>  — 初始化
3. 執行 quality_loop.py run                   — 跑完整 quality loop
4. 回報結果 + 最終報告位置
```

### Agent 內部使用的 Scripts（人類看不到）

| Script | 用途 |
|--------|------|
| `quality_loop.py` | 狀態機，驅動整個流程 |
| `dimension_executor.py` | 執行 12 種 quality tools |
| `crg_wrapper.py` | CRG 結構分析（9 commands）|
| `score.py` | 加權分數計算 |
| `verify.py` | Anti-bias 驗證 |
| `checkpoint.py` | 每輪存檔 |
| `issue_tracker.py` | Issue 持久化追蹤 |
| `report_gen.py` | 最終報告生成 |
| `setup_target.py` | Clone target + CRG check |
| `crg_analysis.py` | CRG metrics 結構化 |
| `llm_router.py` | 統一 MiniMax M2.7 |

---

## 必要前置（Agent 自動處理）

- **Python 3.12**: 系統 `python3` 可能是 3.14，CRG 需要 3.12
  - Agent 自動偵測，若失敗則用 `/opt/homebrew/bin/python3.12`
- **CRG**: 若未安裝，Agent 自動執行 `install_crg.sh`（一次性的 patch script）

---

## 執行階段（State Machine）

```
init → setup → recon → round (最多3輪) → quality_complete
         ↓
     若 crg_available=false → 跳過 recon，直接 round
```

每個 `round` 內部：
```
3a: 執行 12 個 dimension tools → 各自 JSON
3b: score.py 計算加權分數
3c: verify.py 防 bias 驗證
3d: checkpoint.py 存檔
3e: quality_complete 檢查
     → 分數 >= 85 AND 無 open critical/high → 完成
     → 否則 → 3f
3f: 依 severity 順序修復 open issues → 下一輪
```

---

## 12 Quality Dimensions

| # | Dimension | Tool | Weight | Target |
|---|-----------|------|--------|--------|
| 1 | linting | pylint | 0.06 | 95 |
| 2 | type_safety | mypy | 0.10 | 95 |
| 3 | test_coverage | pytest --cov | 0.13 | 80 |
| 4 | security | bandit | 0.10 | 90 |
| 5 | performance | (skip) | 0.07 | 80 |
| 6 | architecture | cloc + CRG | 0.07 | 80 |
| 7 | readability | radon | 0.06 | 85 |
| 8 | error_handling | grep try: | 0.09 | 85 |
| 9 | documentation | grep docstring | 0.10 | 85 |
| 10 | secrets_scanning | gitleaks | 0.08 | 100 |
| 11 | mutation_testing | (skip) | 0.08 | 70 |
| 12 | license_compliance | scancode | 0.06 | 95 |

---

## CRG 整合（若可用）

CRG 提供結構智慧：hub nodes、community cohesion、dead code、架構弱點檢測。
結果寫入 `.sessi-work/crg_reconnaissance.json` 和 `crg_metrics.json`。

若 CRG 不可用，框架自動降級，只做 tool-only 評估。

---

## Anti-Bias 防禦

1. `score = min(tool_score, llm_score)` — tool 是 ground truth
2. 每個 finding 必須有 tool output 證據
3. 每個 fix 前後執行 tool 驗證，確認改善才 commit
4. Δ > 10 無 git diff 證據 → 最多只給 +3
5. 分數下降 → 觸發 revert protocol
6. CRG structural drift — 新 hub nodes 或 risk_score 跳 > 0.2 → 自動註冊 issue

---

## Issue Registry

狀態生命週期：`open` → `fixed` | `deferred` | `wontfix`

優先順序：**severity-first**，不是 score-first。
一個 dimension 可能已達 target，但若有 open critical/high issue 仍必須處理。

---

## 輸出檔案

```
.sessi-work/
├── quality_state.json        ← 當前狀態
├── crg_status.json         ← CRG 可用性
├── crg_reconnaissance.json ← CRG 9 commands 結果
├── crg_metrics.json        ← 結構化 metrics
├── issue_registry.json      ← Issue 追蹤
└── round_<n>/
    ├── scores/             ← 12 個 dimension JSON
    ├── overall_score.json  ← 3b 輸出
    ├── verified.json      ← 3c 輸出
    ├── round_<n>.json    ← 3d 快照
    └── round_<n>.md      ← markdown 摘要
```

---

## Graceful Degradation

| 缺少組件 | 行為 |
|---------|------|
| CRG 未安裝 | 跳過結構分析，tool-only 評估 |
| Tool 未安裝 | Dimension 回傳 `status: "skip"`, score = 100 |
| Config 未找到 | 使用內建預設值 |
| Issue tracker 不可用 | 純分數計算，無 issue 追蹤 |

---

## Error Handling

- Tool not found → `status: "skip"`, score = 100
- Tool timeout → `status: "error"`, score = 0
- Score computation failure → fallback to direct tool score average

---

## 與人類對話時的輸出格式

Agent 完成後，向人類報告：

```
✅ Quality Loop 完成（第 N 輪）

📊 分數：78/85（落後 7 分）
🔴 Open issues：3 critical, 2 high, 5 medium

┌─────────────────────────┬────────┬────────┐
│ Dimension               │ Score  │ Target │
├─────────────────────────┼────────┼────────┤
│ test_coverage           │ 62     │ 80     │ ← failing
│ security                │ 71     │ 90     │ ← failing
│ documentation          │ 74     │ 85     │ ← failing
│ ...                    │        │        │
└─────────────────────────┴────────┴────────┘

🔧 Top Issues:
  🔴 [critical] bandit: hardcoded_password — auth.py:47
  🔴 [critical] bandit: hardcoded_password — config.py:22
  🔴 [high] bandit: 6 more secrets found

📁 報告位置：.sessi-work/final_report.md
```
