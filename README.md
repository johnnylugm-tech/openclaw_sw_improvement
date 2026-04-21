# Harness Quality Framework

Auto-research-style quality improvement for code repositories. Evaluates code across 12 core quality dimensions with optional 5 extended dimensions, identifies gaps, and automatically implements improvements.

## Features

✓ **12 Core Quality Dimensions**
- Linting, Type Safety, Test Coverage, Security, Performance
- Architecture, Readability, Error Handling, Documentation
- Secrets Scanning, Mutation Testing, License Compliance

✓ **5 Extended Dimensions** (optional)
- Property Testing, Fuzzing
- Accessibility, Observability, Supply Chain Security

✓ **Anti-Bias Defenses**
- Tool-first hierarchy: final_score = min(tool_score, llm_score)
- Evidence requirement on all findings
- Per-fix re-verification with revert protocol
- Deterministic verification prevents self-evaluation bias

✓ **Configurable Quality Gates**
- Weighted dimension scoring (normalize across enabled dims)
- Configurable targets per dimension (0-100)
- Early-stop when target reached
- Per-round snapshots with git tagging

## How to Run

> **This is a Claude Code skill — it runs entirely in the conversation window.**
> There is no standalone CLI command. Claude reads `SKILL.md` as its instruction
> set and calls the Python scripts interactively.

### Step 1: Prepare config

```bash
cp config.example.yaml config.yaml
# Edit config.yaml if needed (score_gate, rounds, model, etc.)
```

### Step 2: Open Claude Code and say

```
"Please run the quality improvement skill on /path/to/repo"
# or
"Evaluate https://github.com/user/repo using config.yaml"
# or  
"Run all 12 quality dimensions, 3 rounds, score gate 85"
```

Claude will execute the 4-step process from `SKILL.md` — no further commands needed.

### Advanced: 17 dimensions (core + extended)

```bash
# First time only: install extended tools
./scripts/install_extended_tools.sh --high   # mutation testing (recommended)
./scripts/install_extended_tools.sh --medium # property testing + fuzzing
./scripts/install_extended_tools.sh --all    # everything

# Use advanced config
cp config.advanced.yaml config.yaml
# Edit: set 'enabled: true' for desired extended dims
```

Then in Claude Code conversation:
```
"Run quality improvement using config.advanced.yaml on /path/to/repo"
```

## Configuration

### config.example.yaml
- 12 core dimensions (all enabled by default)
- Target: 85/100
- 3 rounds of improvement
- Early-stop enabled

**Weights** (normalized to 1.0):
```
linting             6%
type_safety        10%
test_coverage      13%
security           10%
performance         7%
architecture        7%
readability         6%
error_handling      9%
documentation      10%
secrets_scanning    8%
mutation_testing    8%
license_compliance  6%
```

### config.advanced.yaml
- All 17 dimensions (12 core + 5 extended)
- 5 extended disabled by default
- Same target/rounds/early-stop as standard
- Adjusted weights when extended dims enabled
- Installation guide included in file

## Core Dimensions (12)

| Dimension | Weight | Target | Tools | Purpose |
|-----------|--------|--------|-------|---------|
| **linting** | 6% | 95 | eslint, pylint, clippy | Code style consistency |
| **type_safety** | 10% | 95 | pyright, rustc, javac | Type correctness |
| **test_coverage** | 13% | 80% | coverage, nyc, tarpaulin | Line/branch coverage |
| **security** | 10% | 90 | bandit, npm-audit, cargo-audit | Vulnerability detection |
| **performance** | 7% | 80 | pytest-benchmark, lighthouse | Speed/efficiency |
| **architecture** | 7% | 80 | sonarqube, codeql | Code organization |
| **readability** | 6% | 85 | radon, complexity tools | Maintainability |
| **error_handling** | 9% | 85 | pytest, jest | Exception/error recovery |
| **documentation** | 10% | 85 | pydocstyle, jsdoc | Code comment coverage |
| **secrets_scanning** | 8% | 100 | detect-secrets, gitleaks | Secret/credential leaks (zero tolerance) |
| **mutation_testing** | 8% | 70 | mutmut, stryker | Test suite quality validation |
| **license_compliance** | 6% | 95 | scancode, fossa | License conflict detection |

## Extended Dimensions (5)

| Dimension | Tools | Priority | Impact | Prerequisites |
|-----------|-------|----------|--------|----------------|
| property_testing | hypothesis, fast-check | MEDIUM | +3% | linting ✓, type_safety ≥ 90% |
| fuzzing | atheris, jazzer | MEDIUM | +3% | security ≥ 85% |
| accessibility | pa11y, axe-core | MEDIUM | +2% | UI code, readability ≥ 80% |
| observability | syft, grype | LOW | +2% | — |
| supply_chain_security | cosign | LOW | +3% | security ≥ 85% |

**With extended dims:** Quality ceiling increases from 70-75% (core dimensions) to 80%+ (full framework).

See `docs/EXTENDED_DIMENSIONS.md` for detailed guide.

## How It Works

### 4-Step Execution

1. **Resolve Configuration** → Load & merge defaults, validate dims
2. **Resolve Target** → Clone repo or use local path, set up git; CRG auto-built
3. **CRG Reconnaissance** *(if CRG installed)* → 9-tool structural scan; pre-seed issues
4. **Iterate Rounds** → Evaluate → Score → Verify → Improve (repeat N times)
5. **Final Report** → Trajectory, evidence, recommendation

### Per-Round Loop

**3a. Evaluate** (per-dimension)
- Run tool checks + LLM analysis
- Reconcile: min(tool_score, llm_score)
- Require evidence for every finding

**3b. Score**
- Aggregate per-dim scores with weights
- Identify failing dimensions by impact
- Check if target reached

**3c. Verify** (anti-bias check)
- Deterministic comparison: pre vs post
- Cap unsupported claims (Δ > 10 needs evidence)
- Surface regressions, enable revert

**3d. Checkpoint**
- Snapshot round results
- Git tag: `round-<n>`
- Generate markdown summary

**3e. Early-Stop**
- If score ≥ target → stop (success)
- If no improvements → stop (plateau)
- Else → continue to improve

**3f. Improve** (auto-research)
- Rank fixes by impact (gap × weight)
- Per-fix: tool verification + revert on regression
- One commit per fix

### Anti-Bias Defenses (12 Layers)

**Original 7 layers:**
1. **Tool-first hierarchy** — LLM claims capped by tool scores
2. **Evidence requirement** — All findings need tool output or git diff
3. **Per-fix re-verification** — Revert if tool shows no improvement
4. **Deterministic verification** — Quantitative pre/post comparison
5. **Regression detection** — Surface changes that hurt other dims
6. **Path heuristics** — Prevent undetected regressions
7. **CRG structural drift** — Architectural regression via hub/risk graph

**New layers (v3.1 — counters: laziness, shortcuts, hallucination, self-congratulation):**
8. **Execution Contract** — behavioral red lines at prompt start
9. **Devil's Advocate** — Gemini Flash challenges Tier 3 before score write
10. **High-Score Gate** — `llm_score ≥ 85` requires negative space proof or caps at 80
11. **Fix Verification Gate** — `mark_fixed()` enforces `commit_sha` + `tool_rerun_path`
12. **Self-Consistency Gate** — flags Δ > 15 with insufficient evidence, tool/LLM divergence

See `docs/ANTI_BIAS.md` for detailed analysis and tuning.

## Code Review Graph Integration (Optional)

The framework integrates with **Code Review Graph (CRG)** — 24 of 27 MCP tools utilized, 6 of them **deeply integrated** via `scripts/crg_analysis.py` — reducing Tier 3 evaluation token cost by 30–50% while surfacing structural issues that dimension tools cannot see.

### What CRG Adds

**Four integration points + one deep-integration layer:**

1. **Structural Reconnaissance (Step 2.5, once per session)** — Before the first evaluation round, 9 CRG queries build a structural intelligence baseline (~3,900 tokens vs ~10,000+ for blind file reading):
   - **High-risk components** — hub + bridge nodes with high centrality
   - **Untested hotspots** — hub nodes in knowledge gaps → pre-seeded as `high` issues
   - **Module cohesion** — low-cohesion communities → pre-seeded as `medium` issues
   - **Unexpected couplings** — surprising cross-module edges → pre-seeded as `medium` issues
   - **Dead code** — unreferenced functions/classes → pre-seeded as `low` issues
   - Outputs `crg_reconnaissance.json` which guides all subsequent dimension evaluations

2. **Tier 3 Evaluation** — Before reading source code, `get_minimal_context` (~100 tokens) orients each dimension evaluation; then dimension-specific tools (hub nodes, bridge nodes, community cohesion, flow analysis) replace blind code reading → **−30 to −50% tokens, better accuracy**

3. **Pre-Fix Context + Safety Gate** — Before each fix:
   - `get_review_context` replaces manual file reads (impact + source + guidance in one call)
   - `get_impact_radius` records hub/bridge status of the modified function
   - risk_score ≥ 0.7 or hub/bridge touch → defer instead of commit (prevents architectural regressions)

4. **Post-Round Structural Verification** — After each round:
   - Detect architectural drift
   - Auto-register test coverage gaps
   - Trigger revert protocol if drift > 0.4

5. **Deep-Integration Layer (`scripts/crg_analysis.py`)** — Turns raw CRG
   outputs into deterministic numeric metrics with explicit thresholds.
   Emits `.sessi-work/crg_metrics.json`, consumed directly by `score.py`:

   | Signal              | Deterministic decision                          |
   |---------------------|-------------------------------------------------|
   | `risk_score`        | eval_depth = deep / standard / fast             |
   | community cohesion  | architecture sub-score (min'd into final score) |
   | flow coverage       | error_handling sub-score (min'd into final score) |
   | dead-code ratio     | escalate low→medium if >5%                      |
   | hub fan-in          | severity bucket critical/high/medium/low        |
   | suggested_questions | auto-seeded registry issues (severity mapped)   |

   All thresholds ENV-overridable (`CRG_RISK_DEEP`, `CRG_COHESION_HEALTHY`,
   etc.). Inspect with `python3 scripts/crg_analysis.py thresholds`.

### Status Check

```bash
# Anytime: see CRG status (auto-initialized by framework at session start)
cat .sessi-work/crg_status.json

# If MCP tools not showing in Claude Code after restart: re-run install
code-review-graph install --platform claude-code --repo .
```

> **Graph build is automatic** — `setup_target.py` detects if the graph is
> missing and runs `code-review-graph build` transparently. No manual step needed.

**Framework behavior:**
- ✓ **With CRG:** -30-50% Tier 3 tokens + architectural safety gates
- ✓ **Without CRG:** Works fine (higher Tier 3 token cost, no safety gates)
- ✓ **Graceful degradation:** All features optional

See `docs/CRG_DEEP_INTEGRATION.md` for the complete workflow diagram, all 6 deep-integration points, threshold table, and data-flow reference.
See `docs/OPERATION_GUIDE.md` for step-by-step operational guide.

## Installation

### Step 1️⃣: Verify Tool Status (Always Run First)

```bash
# Check what's already installed
python3 scripts/verify_tools.py

# See detailed installation guide for missing tools
python3 scripts/verify_tools.py --install-guide
```

**Output shows:**
- ✓ Core tools (must-have)
- ✓ Extended tools (optional)
- ✓ CRG status (optional, recommended)

### Step 2️⃣: Install Missing Tools (First Time Only)

**Core tools:**
- Usually pre-installed (Python, Node, git, etc.)
- If missing: follow guide from `verify_tools.py --install-guide`

**Extended tools (optional, only if needed):**
```bash
# First time: full install
./scripts/install_extended_tools.sh --high   # Mutation testing (foundation)
./scripts/install_extended_tools.sh --medium # Property testing + fuzzing
./scripts/install_extended_tools.sh --low    # License + observability

# Already installed? Skip this step
# (Re-running automatically updates to latest versions)
```

See `docs/INSTALL_EXTENDED_DIMS.md` for detailed per-tool steps.

### Step 3️⃣: CRG Setup (First Time Only, Optional but Recommended)

**First time:**
```bash
# Register CRG MCP tools with Claude Code (one-time)
code-review-graph install --platform claude-code --repo .

# Restart Claude Desktop to load MCP tools
```

> **Graph build is automatic** — no need to run `code-review-graph build` manually.
> The framework detects a missing graph and builds it transparently at session start.

**Already done?** Skip to running the framework.

**Verify:**
```bash
python3 scripts/verify_tools.py --crg
# Or after first run: cat .sessi-work/crg_status.json
```

### Step 4️⃣: Start in Claude Code

```bash
# Copy config (first time only)
cp config.example.yaml config.yaml
```

Then open Claude Code and say:
```
"Please run the quality improvement skill on [this repo / path / URL]"
```

## Quick Start Scenarios

### Scenario 1: First Time Setup (Recommended)

```bash
# Check installed tools
python3 scripts/verify_tools.py

# Install extended tools if needed (optional)
./scripts/install_extended_tools.sh --high

# Setup CRG (optional, recommended for token savings)
code-review-graph install --platform claude-code --repo .
# Restart Claude Desktop (graph is auto-built by framework on first run)

# Prepare config
cp config.example.yaml config.yaml
```
Then in Claude Code: `"Run quality improvement on /path/to/repo"`

### Scenario 2: Already Have Tools

```bash
# Optional: update CRG graph
code-review-graph update --repo .
```
Then in Claude Code: `"Run quality improvement on /path/to/repo"`

### Scenario 3: Full Setup (Extended Tools + CRG)

```bash
# First time only
python3 scripts/verify_tools.py
./scripts/install_extended_tools.sh --all
code-review-graph install --platform claude-code --repo .
# Restart Claude Desktop (graph auto-built on first framework run)

# Configure with all dimensions
cp config.advanced.yaml config.yaml
# Edit: set 'enabled: true' for desired extended dims
```
Then in Claude Code: `"Run quality improvement using config.advanced.yaml"`

### Scenario 4: Subsequent Runs

Nothing to install — just open Claude Code and say:
```
"Run another quality improvement round on [repo]"
```
Optional: keep CRG graph fresh first: `code-review-graph update --repo .`

## Usage

### Conversation Prompts

```
# Standard run (current directory)
"Run the quality improvement skill, config is config.yaml"

# Evaluate a GitHub repo
"Evaluate https://github.com/user/repo — 3 rounds, score gate 85"

# Custom target + config
"Run quality improvement on /path/to/repo using my-config.yaml"

# Single round (quick assessment)
"Run 1 round of quality evaluation on this project"

# All dimensions (extended included)
"Run quality improvement with all 17 dimensions using config.advanced.yaml"
```

### Conversation Options (tell Claude what you want)

```
"Use claude-opus-4 for the improvement phase"
"Only evaluate architecture and security this round"
"Skip mutation testing, focus on linting and type_safety"
"Run with score gate 90 instead of 85"
"Dry-run only: evaluate but don't apply any fixes"
```

## Output Structure

```
.sessi-work/
├── round_1/
│   ├── scores/
│   │   ├── linting.json        # Dimension score + findings
│   │   ├── type_safety.json
│   │   └── ... (one per dimension)
│   ├── tools/
│   │   ├── linting.txt         # Raw tool output
│   │   ├── type_safety.txt
│   │   └── ... (one per dimension)
│   ├── round_1.json            # Round snapshot (all scores + deltas)
│   └── round_1.md              # Human-readable summary
├── round_2/
├── round_3/
└── final_report.md             # Trajectory across rounds
```

Each dimension score includes:
- `score` (0-100)
- `tool_score` (from tools only)
- `llm_score` (from LLM analysis)
- `findings[]` with evidence
- `gaps` (where falling short)
- `tool_outputs` (raw tool stdout)

## Examples

### Example 1: Quick Assessment (1 round)
```bash
cp config.example.yaml config.yaml
# Edit config.yaml: set max_rounds: 1
```
In Claude Code: `"Run 1 round of quality assessment on /path/to/repo"`

### Example 2: Full Framework (17 dimensions)
```bash
cp config.advanced.yaml config.yaml
./scripts/install_extended_tools.sh --all
# Edit config.yaml: enable desired extended dims
```
In Claude Code: `"Run quality improvement using config.advanced.yaml"`

### Example 3: Custom Targets
```bash
cp config.example.yaml config.yaml
# Edit config.yaml:
# quality:
#   score_gate: 90
# dimensions:
#   test_coverage:
#     target: 95
#   security:
#     target: 95
```
In Claude Code: `"Run quality improvement — score gate is 90"`

## Architecture

- **SKILL.md** — Execution contract (Claude reads this as its instruction set)
- **scripts/config_loader.py** — YAML → JSON resolver (called by Claude)
- **scripts/setup_target.py** — Clone/setup working dir (called by Claude)
- **scripts/score.py** — Weighted score computation (called by Claude)
- **scripts/verify.py** — Anti-bias verification (called by Claude)
- **scripts/checkpoint.py** — Round snapshots (called by Claude)
- **prompts/evaluate_dimension.md** — Per-dimension protocol (followed by Claude)
- **prompts/improvement_plan.md** — Fix planning (followed by Claude)
- **prompts/verify_round.md** — Cross-check & revert (followed by Claude)

## Documentation

- **README.md** (this file) — Overview & quick start
- **docs/OPERATION_GUIDE.md** — Complete workflow with CLI + CRG MCP tools
- **docs/INSTALL_EXTENDED_DIMS.md** — Tool installation guide
- **docs/EXTENDED_DIMENSIONS.md** — Detailed guide for 5 extended dims
- **docs/ANTI_BIAS.md** — 12-layer bias defense analysis
- **EXTENDED_DIMS_STATUS.md** — Tool availability & prerequisites

## Performance

- **Standard config** (12 core dims): ~10-20 min per round
- **Extended config** (12 core + 5 extended): ~30-50 min per round
- **Total time** (3 rounds): 30-150 min depending on codebase size

Recommendation: Start with core dimensions, add extended dims (property_testing, fuzzing) as needed.

## Limitations

Framework automates tool-driven improvements across 12 core + 5 extended quality dimensions (17 total). Cannot replace:
- Business logic correctness (requires domain knowledge)
- Real user experience testing (requires humans)
- Zero-day security discovery (requires expert analysis)
- Team-specific code style preferences

See `docs/ANTI_BIAS.md` for detailed automation ceiling analysis.

## Contributing

To extend with new dimensions:
1. Add dimension to `config.example.yaml` & `config.advanced.yaml`
2. Create evaluation protocol in `prompts/`
3. Update weight normalization in `scripts/score.py`
4. Document in `docs/DIMENSIONS.md`

## License

MIT License - See LICENSE file

## References

- Framework: Based on Karpathy's autoresearch pattern (`github.com/karpathy/autoresearch`)
- Quality model: Extended from Harness Engineering framework (base model: 12 core dimensions)
- Implementation: Claude Code skill with Python orchestration + LLM evaluation
