# Installation Guide: Extended Dimensions Tools

This guide covers installing tools required for the 5 extended quality dimensions.
(Note: mutation_testing and license_compliance are now core dimensions and do not require installation here.)

## Quick Start

Install by priority level:

```bash
# HIGH priority (mutation testing - strongest signal)
pip3 install mutmut
npm install -g stryker stryker-cli

# MEDIUM priority (advanced testing + accessibility)
pip3 install hypothesis
npm install -g fast-check pa11y
pip3 install atheris  # Requires Python 3.9+

# LOW priority (compliance + observability)
pip3 install scancode
npm install -g fossa
brew install syft grype cosign
```

## By Package Manager

### pip3 (Python)

```bash
# Mutation Testing
pip3 install mutmut

# Property Testing  
pip3 install hypothesis

# Fuzzing
pip3 install atheris  # Python 3.9+ required

# License Compliance
pip3 install scancode
```

**Verification:**
```bash
pip3 show mutmut hypothesis atheris scancode
```

### npm (JavaScript/Node)

```bash
# Mutation Testing
npm install -g stryker stryker-cli

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

### 1. Mutation Testing (HIGH Priority)
**Purpose:** Verify test suite quality by injecting code mutations

**Tools:**
- `mutmut` (Python) - pytest/unittest support
- `stryker` (JavaScript/Node) - broad language support

**Install:**
```bash
pip3 install mutmut
npm install -g stryker stryker-cli
```

**Verify:**
```bash
mutmut --version
stryker --version
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

### mutmut installation fails
```bash
# Ensure pip3 is up to date
pip3 install --upgrade pip setuptools wheel
pip3 install mutmut
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
