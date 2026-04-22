# Installation Guide: Extended Dimensions Tools

This guide covers installing tools required for the 5 **extended** quality dimensions.

> **Note:** `mutation_testing` is a **CORE** dimension (in `config.example.yaml`).
> It uses `pytest-gremlins`, NOT `mutmut`. Core tools are verified via:
> `python3 scripts/verify_tools.py`
>
> **mutation_testing (core):** `pip install pytest-gremlins`
> **license_compliance (core):** `pip install scancode-toolkit`

## Quick Start

```bash
# CORE dimension tools (already in config.example.yaml)
pip install pytest-gremlins    # mutation_testing
pip install scancode-toolkit   # license_compliance (if extended)

# HIGH priority extended (property testing)
pip3 install hypothesis
npm install -g fast-check

# MEDIUM priority extended (fuzzing + accessibility)
pip3 install atheris  # Requires Python 3.9+
npm install -g pa11y axe-core

# LOW priority extended (observability + supply chain)
brew install syft grype cosign
```

## By Package Manager

### pip3 (Python)

```bash
# Property Testing  
pip3 install hypothesis

# Fuzzing
pip3 install atheris  # Python 3.9+ required
```

**Verification:**
```bash
pip3 show hypothesis atheris
```

### npm (JavaScript/Node)

```bash
# Property Testing
npm install -g fast-check

# Accessibility
npm install -g pa11y axe-core

# License Compliance
npm install -g fossa
```

**Verification:**
```bash
npm list -g stryker fast-check pa11y axe-core fossa
```

### brew (macOS)

```bash
# Observability
brew install syft grype

# Supply Chain Security
brew install sigstore/tap/cosign
```

**Verification:**
```bash
brew list --versions syft grype cosign
```

## By Dimension

### 1. Mutation Testing (CORE — not extended)
**Purpose:** Verify test suite quality by injecting code mutations

**Tool:** `pytest-gremlins` (pytest plugin, NOT mutmut)

> **Why not mutmut?** mutmut has fork/SIGXCPU issues on macOS and creates `mutants/` directory that causes module name collisions with `src/` layouts.
> pytest-gremlins uses AST-level mutation switching — no file-based working directory, fast (3.73x faster), active maintenance.

**Install:**
```bash
pip install pytest-gremlins
```

**Verify:**
```bash
pytest --help | grep gremlins  # should show --gremlins flag
```

### 2. Property Testing (MEDIUM Priority)
**Purpose:** Generate test cases automatically from properties

**Tools:**
- `hypothesis` (Python) - generates edge cases
- `fast-check` (JavaScript) - property-based testing

**Install:**
```bash
pip3 install hypothesis
npm install -g fast-check
```

**Verify:**
```bash
python3 -c "import hypothesis; print(hypothesis.__version__)"
npm list -g fast-check
```

### 3. Fuzzing (MEDIUM Priority)
**Purpose:** Continuous input mutation for crash discovery

**Tools:**
- `atheris` (Python 3.9+) - fuzzer from Google
- `jazzer` (Java) - JVM fuzzing (optional, requires Java)

**Install:**
```bash
# Python fuzzing
pip3 install atheris

# Java fuzzing (optional - requires Java 11+)
# Requires manual setup or Docker
```

**Verify:**
```bash
python3 -c "import atheris; print(atheris.__version__)"
```

### 4. License Compliance (LOW Priority)
**Purpose:** Track and verify open source license compatibility

**Tools:**
- `scancode` (Python) - license scanner from nexB
- `fossa` (npm/SaaS) - dependency tracking

**Install:**
```bash
pip3 install scancode
npm install -g fossa
```

**Verify:**
```bash
scancode --version
fossa --version
```

### 5. Accessibility (MEDIUM Priority)
**Purpose:** Detect WCAG violations and a11y issues

**Tools:**
- `pa11y` (npm) - automated a11y testing
- `axe-core` (npm) - axe accessibility engine

**Install:**
```bash
npm install -g pa11y axe-core
```

**Verify:**
```bash
pa11y --version
npm list -g axe-core
```

### 6. Observability (LOW Priority)
**Purpose:** Detect gaps in logging, metrics, tracing

**Tools:**
- `syft` (brew) - SBOM generator from Anchore
- `grype` (brew) - vulnerability scanner

**Install:**
```bash
brew install syft grype
```

**Verify:**
```bash
syft --version
grype --version
```

### 7. Supply Chain Security (LOW Priority)
**Purpose:** Verify artifact signatures and provenance

**Tools:**
- `cosign` (brew/sigstore) - container/artifact signing

**Install:**
```bash
brew install sigstore/tap/cosign
# or
brew install cosign
```

**Verify:**
```bash
cosign version
```

## Installation Priority Rationale

### HIGH: Mutation Testing
- **Why:** Test quality is foundational. Weak tests mask other improvements
- **Signal:** Reveals coverage gaps and missing edge cases
- **ROI:** Usually finds 3-5 regressions per 100 mutations
- **Time:** ~5-15 min per test suite

### MEDIUM: Property Testing, Fuzzing, Accessibility
- **Why:** Catch specific classes of hard-to-find bugs
- **Property Testing:** Generates edge cases automatically
- **Fuzzing:** Finds crash/security issues
- **Accessibility:** Legal + UX requirement
- **ROI:** 2-3 new findings per session

### LOW: License, Observability, Supply Chain
- **Why:** Governance + hardening, fewer finds but important
- **License:** Compliance risk
- **Observability:** Production readiness
- **Supply Chain:** Security posture
- **ROI:** 1-2 findings per session, mostly prevention

## Troubleshooting

### pytest-gremlins installation fails
```bash
# Ensure pip is up to date
pip install --upgrade pip
pip install pytest-gremlins
# Verify
pytest --co --help | grep gremlins
```

### stryker not found in PATH (npm)
```bash
# Check npm global bin path
npm config get prefix
# Should be /usr/local or ~/.npm-global

# Add to PATH if needed
export PATH="$(npm config get prefix)/bin:$PATH"
```

### atheris requires Python 3.9+
```bash
# Check Python version
python3 --version

# If < 3.9, skip atheris or use venv with Python 3.9+
python3.9 -m venv /tmp/py39
source /tmp/py39/bin/activate
pip install atheris
```

### cosign on macOS
```bash
# Try alternate tap if standard fails
brew tap sigstore/tap
brew install sigstore/tap/cosign

# Or download binary directly
curl -L https://github.com/sigstore/cosign/releases/download/v2.0.0/cosign-darwin-amd64
chmod +x cosign-darwin-amd64
sudo mv cosign-darwin-amd64 /usr/local/bin/cosign
```

## Enabling Extended Dimensions

Once tools are installed, enable in `config.advanced.yaml`:

```yaml
mutation_testing:
  enabled: true  # Change to true

property_testing:
  enabled: true

fuzzing:
  enabled: true

license_compliance:
  enabled: true

accessibility:
  enabled: true

observability:
  enabled: true

supply_chain_security:
  enabled: true
```

## Notes

- **Disk space:** Full tool suite ~500MB (mostly node_modules)
- **Runtime:** Extended dims add 10-20 min per round (opt-in)
- **Dependencies:** Most tools are self-contained; some (pa11y, fossa) need optional browser/cloud config
- **Python compatibility:** atheris needs Python 3.9+; others work with 3.8+
- **Node compatibility:** All npm tools require Node 14+
