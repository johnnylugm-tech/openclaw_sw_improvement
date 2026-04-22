# Extended Dimensions: Tool Availability Status Report

**Date:** 2026-04-18  
**Scope:** 5 extended quality dimensions + 9 tools  
**Status:** ⚠️ 8/9 tools installed — jazzer (Java fuzzing) requires Java 11+ (optional)

## Summary

8 of 9 tools required for extended dimensions are installed and ready to use.
(Note: mutation_testing and license_compliance are now core dimensions — not extended)

**jazzer** (Java fuzzing) is the one missing tool — it requires Java 11+.
All other fuzzing capability is available via `atheris` (Python). `jazzer` is
optional: skip it if your codebase is not Java/JVM-based.

**Versions installed:**
- mutmut 3.3.1, hypothesis 6.141.1, atheris 2.3.0 (Python 3.9 compat), scancode-toolkit 32.4.1
- stryker (legacy) + @stryker-mutator/core (modern), fast-check, pa11y, axe-core, fossa
- syft 1.42.4, grype 0.111.0, cosign 3.0.6

## Tool Installation Status

### ✓ READY (12 Core Dimensions)
- All tools for 12 core dimensions are installed and operational
- pyright, eslint, pytest, coverage, clippy, checkstyle, mutmut, scancode, gitleaks, etc. ✓
- mutation_testing and license_compliance are NOW CORE (not extended)

### ✓ READY (5 Extended Dimensions)
- 8/9 extended tools installed (jazzer missing — optional for non-Java repos)
- Enable each dimension by setting `enabled: true` in `config.advanced.yaml`

## Detailed Status by Dimension

### Core Dimensions (in config.example.yaml)
| Dimension | Tier | Status | Notes |
|-----------|------|--------|-------|
| linting | 1 | ✓ core | eslint, pylint |
| type_safety | 1 | ✓ core | pyright |
| test_coverage | 1 | ✓ core | coverage, nyc |
| security | 2 | ✓ core | bandit, npm-audit |
| secrets_scanning | 1 | ✓ core | detect-secrets, gitleaks |
| mutation_testing | 1 | ✓ core | pytest-gremlins, mutmut (deprecated — has fork/SIGXCPU issues on macOS) |
| license_compliance | 1 | ✓ core | scancode-toolkit, fossa |
| architecture | 3 | ✓ core | radon, sonarqube |
| readability | 3 | ✓ core | radon |
| error_handling | 3 | ✓ core | custom checks |
| documentation | 3 | ✓ core | pydocstyle, interrogate |
| performance | 3 | ✓ core | radon, pytest-benchmark |

### Extended Dimensions (in config.advanced.yaml, disabled by default)
| Dimension | Tools | Status | Priority | Notes |
|-----------|-------|--------|----------|-------|
| **property_testing** | hypothesis, fast-check | ✓ 2/2 | MEDIUM | Generates edge cases |
| **fuzzing** | atheris 2.3.0, jazzer | ✓ 1/2 | MEDIUM | atheris ✓, jazzer needs Java 11+ |
| **accessibility** | pa11y, axe-core | ✓ 2/2 | MEDIUM | WCAG compliance |
| **observability** | syft, grype | ✓ 2/2 | LOW | SBOM + vuln scanning |
| **supply_chain_security** | cosign | ✓ 1/1 | LOW | Signature verification |

## Installation by Priority

### Priority 1: HIGH (Mutation Testing)
```bash
# ~5 min install time
pip3 install mutmut
npm install -g stryker stryker-cli
```

**Why First:**
- Test quality is foundational
- Reveals test coverage gaps
- Impacts all other dimensions

**Expected Impact:**
- +3-5 regressions found per 100 mutations
- Usually requires 2-4 test improvements

---

### Priority 2: MEDIUM (Property Testing, Fuzzing, Accessibility)

**Property Testing:**
```bash
pip3 install hypothesis
npm install -g fast-check
```
- Generates edge case test data
- Finds subtle bugs in logic

**Fuzzing:**
```bash
pip3 install atheris  # Requires Python 3.9+
```
- Continuous input mutation
- Finds crash/security vulnerabilities

**Accessibility:**
```bash
npm install -g pa11y axe-core
```
- WCAG 2.1 compliance
- Required for public-facing UIs

---

### Priority 3: LOW (Compliance, Observability, Supply Chain)

**License Compliance:**
```bash
pip3 install scancode
npm install -g fossa
```

**Observability:**
```bash
brew install syft grype
```

**Supply Chain Security:**
```bash
brew install sigstore/tap/cosign
```

## Installation Options

### Option A: Install All (Recommended for Complete Framework)
```bash
./scripts/install_extended_tools.sh --all
```

### Option B: Staged Installation
```bash
# Stage 1: Mutation testing (foundation)
./scripts/install_extended_tools.sh --high

# Stage 2: Advanced testing + accessibility
./scripts/install_extended_tools.sh --medium

# Stage 3: Governance + hardening
./scripts/install_extended_tools.sh --low
```

### Option C: Manual Installation
See `docs/INSTALL_EXTENDED_DIMS.md` for per-tool installation steps.

## Configuration Changes Required

After installing tools, enable **extended** dimensions in `config.advanced.yaml`
(mutation_testing and license_compliance are already enabled in `config.example.yaml`
as core dimensions — no action needed for those):

```yaml
# config.advanced.yaml — change from 'enabled: false' to 'enabled: true'
property_testing:
  enabled: true

fuzzing:
  enabled: true

accessibility:
  enabled: true

observability:
  enabled: true

supply_chain_security:
  enabled: true
```

## Verification Steps

After installation:

```bash
# Verify all tools
./scripts/install_extended_tools.sh

# Or verify individually
pip3 show mutmut hypothesis atheris scancode
npm list -g stryker fast-check pa11y axe-core fossa
brew list --versions syft grype cosign
```

## System Requirements

| Tool | Min Version | Notes |
|------|-------------|-------|
| Python | 3.8+ | atheris requires 3.9+ |
| Node.js | 14+ | npm tools |
| macOS | 10.15+ | brew tools (syft, grype, cosign) |
| Java | 11+ | jazzer (optional, fuzzing) |

## Performance Impact

Adding extended dimensions increases analysis time:

- **Standard (12 core dims):** ~5-10 min per round
- **Extended (17 dims):** ~15-25 min per round
- **All enabled:** ~30-40 min per round (full analysis)

Recommendation: Start with HIGH priority (mutation_testing) then add others as needed.

## Architecture Impact

Extended dimensions fit cleanly into existing framework:

✓ Weight normalization auto-adjusts across 17 vs 12  
✓ Prerequisite checks prevent running advanced dims without foundations  
✓ Early-stop still works across all dimensions  
✓ Per-dim evaluation and verification unchanged  
✓ Evidence-gating applies to all extended dims  

## Known Limitations

1. **Mutation Testing (mutmut):** Requires pytest-compatible test structure
2. **Fuzzing (atheris):** Python 3.9+ only; requires fuzz target functions
3. **License (scancode):** May flag transitive dependencies as issues
4. **Accessibility (pa11y):** Web apps only; headless browser required
5. **Observability:** Best with structured logging framework
6. **Supply Chain (cosign):** Requires Sigstore setup for key management

## Troubleshooting

See `docs/INSTALL_EXTENDED_DIMS.md` for:
- Installation failures per tool
- PATH configuration issues
- Version compatibility notes
- macOS-specific (brew) workarounds

## Next Steps

1. **Now:** Read `docs/INSTALL_EXTENDED_DIMS.md`
2. **Choose:** Which priority level to start with
3. **Install:** Run `./scripts/install_extended_tools.sh [--high|--medium|--low|--all]`
4. **Verify:** Confirm all tools are in PATH
5. **Configure:** Update `config.advanced.yaml` with enabled: true
6. **Test:** Run framework with `--config config.advanced.yaml`

## References

- Installation guide: `docs/INSTALL_EXTENDED_DIMS.md`
- Extended dimensions guide: `docs/EXTENDED_DIMENSIONS.md`
- Architecture: `docs/ARCHITECTURE.md`
- Anti-bias defenses: `docs/ANTI_BIAS.md`
