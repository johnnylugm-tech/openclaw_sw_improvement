# Comparison: software_self_improvement vs. openclaw_sw_improvement

**Source:** [johnnylugm-tech/software_self_improvement](https://github.com/johnnylugm-tech/software_self_improvement) (Claude Code + MCP)  
**Target:** [johnnylugm-tech/openclaw_sw_improvement](https://github.com/johnnylugm-tech/openclaw_sw_improvement) (OpenClaw conversation)

---

## Category 1: Original移植差異（從一開始就有）

這些差異是平臺移植時的必然變更，非今日改動。

| 項目 | software_self_improvement (source) | openclaw_sw_improvement (target) | 原因 |
|------|----------------------------------|----------------------------------|------|
| **執行環境** | Claude Code + MCP | OpenClaw conversation | 目標平臺不同 |
| **CRG 整合** | MCP tools（10 個 `mcp__code-review-graph__*`）| Direct Python import + CLI（非 MCP）| OpenClaw 無 MCP，改用 `crg_integration.py` 直接呼叫 |
| **LLM 路由** | Tier 1/2 → Gemini Flash (MCP)，Tier 3 → Claude native | Tier 1/2 → Gemini API key（env `HARNESS_GEMINI_MODEL`），Tier 3 → MiniMax-M2.7 | 移除 MCP，依賴 OpenClaw 內建模組 |
| **CLI 呼叫方式** | Claude 直接 call MCP tools | Agent 呼叫 `python3 scripts/*.py` shell commands | OpenClaw 架構限制 |
| **CLAUDE.md** | 參考 `mcp__code-review-graph__*` tools | 移除 MCP tool 說明（不適用）| 純文件更新 |
| **SKILL.md** | "Claude Code skill"、"Claude reads SKILL.md"、"Claude calls" | "OpenClaw skill"、"Agent reads SKILL.md"、"Agent calls" | 平臺術語替換 |
| **evaluate_dimension.md** | 有 MCP provider 欄位（`mcp__gemini-cli__ask-gemini`）| 移除 provider 欄位，寫 "Use default LLM (agent)" | LLM 路由在 `llm_router.py` 處理 |
| **CRG 初始化** | Claude Code 內建 MCP tool | `scripts/setup_target.py` + `install_crg.sh`（新增 shell script）| OpenClaw 需手動觸發 CRG |
| **Devil's Advocate 說明** | "Gemini Flash challenges Tier 3" | "Secondary LLM call challenges Tier 3" | 抽象化，不特定 gemini |
| **llm_router.py** | Tier 3 用 `claude_native` + `_CLAUDE_MODEL`，有 `IMPROVE_CONFIG` | Tier 3 用 `minimax` + `_MINIMAX_MODEL`，移除 `IMPROVE_CONFIG` | 模型切換 |
| **Prompt 模板** | 有 `mcp__gemini-cli__ask-gemini` prompt | 簡化為 `Use default LLM (agent)` | OpenClaw 不走 MCP |

---

## Category 2: 今日改動（2026-04-22）

### Commit fdc6c5e — mutation_testing 工具替換

| 檔案 | 變更 | 原因 |
|------|------|------|
| `prompts/evaluate_dimension.md` | `mutmut run` → `pytest --gremlins --gremlin-report=json` | mutmut 有 SIGXCPU + module name bug，pytest-gremlins 更快更穩（3.73x faster parallel） |
| `EXTENDED_DIMS_STATUS.md` | 工具名：mutmut → pytest-gremlins | 反映實質工具變更 |

### Commit 98ac6dd — 完整審計修復（6 個檔案）

| 檔案 | 變更 | 原因 |
|------|------|------|
| `scripts/verify_tools.py` | type_safety: mypy → pyright | evaluate_dimension.md + config.example.yaml 都用 pyright，verify_tools 落後 |
| `scripts/verify_tools.py` | 新增 mutation_testing（原本只有 7 個，現在 8 個）| core dimension 少一個工具驗證，覆蓋率僅 58% |
| `scripts/verify_tools.py` | pytest-gremlins 檢測邏輯（pytest plugin 非 standalone cmd）| 修正檢測方式 |
| `scripts/install_extended_tools.sh` | 移除 `--high` 的 mutmut + stryker | mutation_testing 是 CORE 不是 extended |
| `scripts/install_extended_tools.sh` | 重排優先順序：high=property_testing, medium=fuzzing+a11y, low=observability+supply | 移除 mutation_testing 後的順位的自然調整 |
| `scripts/install_extended_tools.sh` | 新增 `log_core_required()` 說明核心工具安裝方式 | 提供正確指引 |
| `docs/INSTALL_EXTENDED_DIMS.md` | 重寫開頭說明（mutation_testing 是 CORE，用 pytest-gremlins）| 移除所有 mutmut 引用 |
| `docs/INSTALL_EXTENDED_DIMS.md` | Section 1 從 "Mutation Testing (HIGH Priority)" 改為 "CORE — not extended" | 反映真實分類 |
| `docs/INSTALL_EXTENDED_DIMS.md` | 故障排除：mutmut → pytest-gremlins | 對應工具變更 |
| `README.md` | mutation_testing 工具：mutmut, stryker → pytest-gremlins | 反映實質變更 |
| `README.md` | `./install_extended_tools.sh --high` 備註：mutation testing → property testing | 避免誤解 |
| `IMPLEMENTATION_STATUS.md` | mutmut ❌ → pytest-gremlins ✅ | 反映工具狀態 |
| `docs/EXTENDED_DIMENSIONS.md` | 添加 Note：mutation_testing 是 CORE，mutmut 標記 DEPRECATED | 說明切換原因 |

---

## 附錄：install_extended_tools.sh 優先順序爭議說明

**爭議點：** `--high` 的內容從 `mutation_testing (mutmut)` 改為 `property_testing (hypothesis)`。

**背景：**
- software_self_improvement 設計中，mutation_testing 排在最高優先（--high），因為它是「最高價值的維度」
- 但 mutation_testing 早已是 CORE dimension，不屬於 extended
- 移除後，high/medium/low 三層的對應關係是一次性重排的（不必然如此，可爭議）

**三種可能的修復方式：**
1. 只移除 mutation_testing，其他兩層不動（最小改動）
2. 重排 high=property_testing, medium=fuzzing+a11y, low=observability+supply（已實施）
3. 廢除優先順序概念，改用 dimension 名稱明確指定

---

## Category 3: anti-bias v3.1 同步（2026-04-23）

今日同步 source software_self_improvement 的 anti-bias v3.1（Layers 8-12 新增）。

**同步的檔案：**

| 檔案 | 變更 | 說明 |
|------|------|------|
| `docs/ANTI_BIAS.md` | 從 source 完整移植 | Layers 8-12 全部到位，含 v3.1 更新說明 |
| `prompts/evaluate_dimension.md` | 嵌入式引用 | Layer 8 Execution Contract + Layer 9 DA prompt + Layer 10 高分確認 |
| `scripts/verify.py` | Layer 12 Self-Consistency Gate | `self_consistency_gate()` 功能已實作 |
| `scripts/issue_tracker.py` | Layer 11 Fix Verification Gate | `mark_fixed()` enforce tool_rerun_path |

**OpenClaw 適配差異：**

| 項目 | Source | OpenClaw | 原因 |
|------|--------|----------|------|
| Layer 9 DA provider | "Gemini Flash" | "Secondary LLM call" | OpenClaw 不走 Gemini MCP，抽象化 |
| CRG access | MCP tools (27 tools) | CLI (`crg_integration.py`) | OpenClaw 無 MCP，改用 direct Python |

**COMPARISON.md 覆蓋狀態：**
- Category 1（平臺移植差異）：✅ 已記錄 CRG MCP → CLI + LLM 路由替換
- Category 3（本節）：✅ 新增
- 缺口：無（所有 v3.1 功能均已同步並適配）

---

*最後更新：2026-04-22 by sub-agent audit*

---

## 未記錄差異補充（2026-04-23 補充）


### D1：IMPROVE_CONFIG 從 llm_router.py 移除

- Source 有 `"improve": {"provider": "claude_native"}`（給 improvement agent 用的 special routing）
- OpenClaw 版本：llm_router.py 已無此欄位，改由 config 統一指定 MiniMax
- 理由：OpenClaw 是單一模型架構，無需 special routing 分流
- 影響：若未來要支援 multi-model，需恢復此 routing 邏輯

### D2：mutation_testing 工具 — 刻意技術分歧

| | software_self_improvement | openclaw_sw_improvement |
|--|--|--|
| 選擇 | mutmut（保留） | pytest-gremlins（替換） |
| 理由 | 4 個月新、60× 少下載、需 Python 3.11+ | SIGXCPU timeout + module collision + 3.73× faster |
| 狀態 | **穩定** | **穩定** |

這是兩個 repo 的**刻意技術分歧**，未來同步時不應覆蓋。如需重新評估，以效能數據（timeout rate、parallel speed）為準。

### D3：--high 優先順序重排（待確認）

- 原始設計：mutation_testing 是 highest-value dimension，故排在 --high
- 修復後：mutation_testing 是 CORE 不屬於 extended，--high 改為 property_testing
- 三種方案（見上文）已列出，最後更新選了方案二（重排 high/medium/low）
- **狀態：爭議未解決**，建議在 README.md 明確標記篩選層級說明

### D4：Devil's Advocate 段落重寫

- Source（evaluate_dimension.md）：包含 "Gemini Flash challenges Tier 3" 明確提及
- OpenClaw 版本：移除 provider 特定文字，改為 "Secondary LLM call challenges Tier 3"
- 理由：OpenClaw 不走 Gemini MCP，抽象化為通用 LLM 描述
- COMPARISON.md 記錄：✅ 本節（D4）已明確記錄（2026-04-23 補充）
