# Extended Dimensions Guide

This guide covers the 5 optional extended quality dimensions that increase the automation ceiling from 70-75% to 80%+.
(Note: mutation_testing and license_compliance are now core dimensions.)

## Quick Reference

> **Note:** `mutation_testing` and `license_compliance` are **core dimensions**
> (enabled by default in `config.example.yaml`), not extended. The 5 extended
> dimensions below are disabled by default and require separate tool installation.

| Dimension | Priority | Impact | Tools | Prerequisites | Details |
|-----------|----------|--------|-------|----------------|---------|
| **property_testing** | MEDIUM | +3% | hypothesis, fast-check | linting ✓, type_safety ≥90% | Edge case generation |
| **fuzzing** | MEDIUM | +3% | atheris, jazzer | security ≥85%, error_handling ≥80% | Crash discovery |
| **accessibility** | MEDIUM | +2% | pa11y, axe-core | readability ≥80% (UI only) | WCAG violations |
| **observability** | LOW | +2% | syft, grype | — | Logging/metrics gaps |
| **supply_chain_security** | LOW | +3% | cosign | security ≥85% | Signature verification |

## 1. Mutation Testing

**Purpose:** Validates test suite quality by injecting code mutations.

### What It Does

Mutation testing modifies the code under test (mutations) and runs the test suite against each mutation:
- If a test fails on the mutation → test is effective ✓
- If a test passes on the mutation → test is weak (mutation "survived") ✗

### Why It Matters

Test coverage (line coverage) is necessary but not sufficient:
```python
def validate_email(email):
    if "@" in email:        # ← Line covered by test
        return True
    return False

# This passes test coverage at 100% but mutation testing would reveal:
# - Mutation: if "@" in email → if True → Test fails? (reveals weak assertion)
# - Mutation: return True → return False → Test catches? (reveals good test)
```

### Tools

- **mutmut** (Python) — pytest-compatible
- **stryker** (JavaScript/TypeScript) — jest/mocha compatible

### Prerequisites

- Test coverage ≥ 70% (no point mutating untested code)
- Tests run in < 10 min (mutation testing is slow)

### Score Formula

```
mutation_score = (killed_mutations / total_mutations) × 100
```

- killed_mutations: Mutations caught by failing tests
- total_mutations: Mutations generated

### Typical Gaps Found

- Missing assertions in happy path
- No error validation
- Incomplete boundary checks
- Weak exception assertions

### Configuration

```yaml
mutation_testing:
  enabled: true
  target: 70          # 70% mutation kill rate
  tools: [mutmut, stryker]
```

---

## 2. Property Testing

**Purpose:** Automatically generates test cases from properties.

### What It Does

Property-based testing specifies invariants the code should maintain, then generates hundreds of random inputs to test them:

```python
@given(st.integers())
def test_multiply_by_two(x):
    """Property: multiply_by_two always returns even number"""
    result = multiply_by_two(x)
    assert result % 2 == 0
```

### Why It Matters

Manual test cases miss edge cases:
```python
def divide(a, b):
    return a / b

# Manual test: divide(10, 2) = 5 ✓
# Property testing reveals: divide(0, 0) → ZeroDivisionError ✗
```

### Tools

- **hypothesis** (Python) — Generates edge cases + shrinks failures
- **fast-check** (JavaScript) — Combinatorial test generation

### Prerequisites

- Linting ✓ (clean code required)
- Type safety ≥ 90% (helps property generation)

### Score Formula

```
property_score = (successful_properties / total_properties) × 100
```

### Typical Gaps Found

- Unhandled edge cases (0, -1, null, empty)
- Boundary condition bugs
- Type coercion issues
- Off-by-one errors

### Configuration

```yaml
property_testing:
  enabled: true
  target: 75
  tools: [hypothesis, fast-check]
```

---

## 3. Fuzzing

**Purpose:** Continuous input mutation for crash/vulnerability discovery.

### What It Does

Fuzzing feeds random/mutated input data to code and monitors for crashes:

```
Input: "hello"
Mutate: "hell\x00"
Feed to function → Crash? Hang? Vulnerability?
```

### Why It Matters

Security testing without fuzzing misses crash vulnerabilities:
```python
def parse_json(data):
    # What if data is: [], {}{}, or binary garbage?
    # What if data contains null bytes?
    return json.loads(data)
```

### Tools

- **atheris** (Python 3.9+) — libFuzzer integration
- **jazzer** (Java/JVM) — Fuzzer for Java

### Prerequisites

- Security ≥ 85% (need baseline security posture)
- Error handling ≥ 80% (need graceful failure)

### Score Formula

```
fuzzing_score = (crashes_fixed / crashes_found) × 100
```

### Typical Gaps Found

- Buffer overflows
- Null pointer dereferences
- Stack overflows
- Resource exhaustion
- Parser crashes

### Configuration

```yaml
fuzzing:
  enabled: true
  target: 70
  tools: [atheris, jazzer]
```

---

## 4. License Compliance

**Purpose:** Track and verify open source license compatibility.

### What It Does

Scans code and dependencies for license declarations and checks compatibility:

```
found: MIT, Apache-2.0, GPL-3.0
conflict? MIT + GPL-3.0 can conflict in proprietary software
```

### Why It Matters

License violations create legal risk:
- GPL requires source code disclosure (incompatible with proprietary)
- Some licenses forbid commercial use
- Combined licenses may conflict

### Tools

- **scancode** (Python) — License detection from nexB
- **fossa** (SaaS) — Dependency license tracking

### Prerequisites

None. Can run anytime.

### Score Formula

```
license_score = (compatible_licenses / total_licenses) × 100
```

### Typical Gaps Found

- Undeclared dependencies
- License conflicts in transitive deps
- Incompatible license combinations
- Outdated license files

### Configuration

```yaml
license_compliance:
  enabled: true
  target: 95
  tools: [scancode, fossa]
```

---

## 5. Accessibility

**Purpose:** Detects WCAG 2.1 Level AA violations.

### What It Does

Automated accessibility testing finds:
- Missing alt text on images
- Low color contrast
- Keyboard navigation gaps
- Semantic HTML issues
- Screen reader problems

### Why It Matters

Accessibility is both legal requirement and UX improvement:
- Legal: ADA/AODA require WCAG AA compliance
- UX: Better keyboard navigation helps power users
- Inclusive: Helps users with disabilities

### Tools

- **pa11y** (npm) — Automated accessibility testing
- **axe-core** (npm) — Accessibility rules engine

### Prerequisites

- Readability ≥ 80% (UI code must be readable to be accessible)
- UI code only (not applicable to APIs)

### Score Formula

```
accessibility_score = ((total_elements - violations) / total_elements) × 100
```

### Typical Gaps Found

- Missing alt text
- Color contrast violations
- Missing labels on form fields
- Keyboard navigation gaps
- Missing ARIA attributes
- Inaccessible modals

### Configuration

```yaml
accessibility:
  enabled: true
  target: 85
  tools: [pa11y, axe-core]
```

---

## 6. Observability

**Purpose:** Detects gaps in logging, metrics, tracing.

### What It Does

Analyzes code for observability completeness:
- Logging at critical points (entry, exit, errors)
- Metrics for key operations
- Trace instrumentation
- Error context preservation

### Why It Matters

Production readiness requires observability:
```python
def process_payment(amount):
    # Missing: logging, metrics, error context
    if amount < 0:
        return False  # ← What went wrong? Unknown in logs
    
    # Better: with observability
    if amount < 0:
        logger.error("Invalid amount", amount=amount, user_id=user_id)
        metrics.increment("payment.invalid_amount")
        raise ValueError(f"Amount must be positive: {amount}")
```

### Tools

- **syft** (brew) — SBOM (Software Bill of Materials) generator
- **grype** (brew) — Vulnerability scanner (SBOM analysis)

### Prerequisites

None. Can run anytime.

### Score Formula

```
observability_score = (instrumented_functions / total_functions) × 100
```

### Typical Gaps Found

- No logging in critical paths
- No error context
- Missing metrics
- No distributed trace headers
- Silent failures

### Configuration

```yaml
observability:
  enabled: true
  target: 80
  tools: [syft, grype]
```

---

## 7. Supply Chain Security

**Purpose:** Verify artifact signatures and provenance.

### What It Does

Ensures code and artifacts are signed/verified:
- Container images signed with cosign
- Release artifacts have provenance
- Dependencies verified as authentic
- Build reproducibility

### Why It Matters

Supply chain attacks are growing risk:
- Attacker compromises dependency
- Users pull malicious version
- Prevention: verify signatures, check provenance

### Tools

- **cosign** (sigstore) — Container and artifact signing

### Prerequisites

- Security ≥ 85% (supply chain security is advanced hardening)

### Score Formula

```
supply_chain_score = (signed_artifacts / total_artifacts) × 100
```

### Typical Gaps Found

- Unsigned container images
- Missing provenance
- No dependency pinning
- No SBOMs
- Unverified build process

### Configuration

```yaml
supply_chain_security:
  enabled: true
  target: 80
  tools: [cosign]
```

---

## Impact Analysis: Standard vs Extended

### Score Ceiling Without Extended Dims

With 12 core dimensions alone:
- Linting, type safety, test coverage, security, performance, architecture, readability,
  error handling, documentation, secrets scanning, mutation testing, license compliance
- **Realistic ceiling: 70-75%** (what tools can directly measure)

**Why?** Standard tools measure:
- Code style consistency ✓
- Type correctness ✓
- Test line coverage ✓
- Known vulnerabilities ✓
- Performance regressions ✓
- Naming clarity ✓

Standard tools DON'T measure:
- Test suite effectiveness (mutation testing)
- Edge case handling (property testing)
- Crash robustness (fuzzing)
- Legal compliance (license)
- User accessibility (a11y)
- Production readiness (observability)
- Artifact integrity (supply chain)

### Score Ceiling With All 16 Dimensions

With extended dimensions:
- **New ceiling: 75-80%**
- Additional +5-10% of measurable quality gains

### Breakdown by Dimension

| Dimension | Contribution |
|-----------|--------------|
| Mutation testing | +3-5% (test suite quality) |
| Property testing | +3% (edge case coverage) |
| Fuzzing | +3% (crash safety) |
| Accessibility | +2% (user experience) |
| License compliance | +1% (legal compliance) |
| Observability | +2% (production readiness) |
| Supply chain | +3% (integrity assurance) |
| **TOTAL** | **+17-19%** (absolute, ~20% relative) |

### Absolute Limitation: 75-80%

**Still cannot reach 90%+ because:**

1. **Business Logic Correctness** (requires domain expertise)
   - No tool knows if the business requirements are correct
   - No tool validates business rule implementations
   - Requires manual verification by domain experts

2. **Real User Experience** (requires humans)
   - Automated accessibility finds technical violations but not UX issues
   - Real users may struggle despite WCAG compliance
   - Requires user testing

3. **Zero-Day Security** (requires expert analysis)
   - Automated tools find known vulnerabilities
   - New vulnerability classes require security research
   - Requires security experts

4. **Team Preferences** (requires human judgment)
   - Code style preferences vary by team
   - Architecture decisions reflect team values
   - Requires team alignment, not automation

## Enabling Extended Dimensions

### Installation

See `docs/INSTALL_EXTENDED_DIMS.md` for detailed steps.

Quick install:
```bash
./scripts/install_extended_tools.sh --all  # Install all 13 tools
```

### Configuration

In `config.advanced.yaml`, set `enabled: true` for dimensions you installed tools for:

```yaml
mutation_testing:
  enabled: true    # Change from false

property_testing:
  enabled: true

# ... other dimensions
```

### Running with Extended Dims

```bash
# Prepare config
cp config.advanced.yaml config.yaml
# Edit: set 'enabled: true' for desired dims
```
Then in Claude Code: `"Run quality improvement using config.advanced.yaml"`

## Best Practices

### Start Incrementally

1. **Begin with mutation_testing** (HIGH priority)
   - Most impactful, reveals test suite gaps
   - Takes longest, plan time accordingly

2. **Add property_testing + accessibility** (MEDIUM priority if applicable)
   - Property testing finds subtle bugs
   - Accessibility required for public UI

3. **Add fuzzing if security-critical** (MEDIUM if relevant)
   - Critical for parsers, protocols, APIs
   - Less critical for business logic

4. **Add compliance + observability** (LOW priority, governance)
   - Required by compliance frameworks
   - Essential for production systems

### Dimension Prerequisites

**Always respect prerequisites:**

```yaml
mutation_testing:
  # PREREQUISITE: test_coverage >= 70%
  enabled: true

property_testing:
  # PREREQUISITES: linting ✓, type_safety >= 90%
  enabled: true

fuzzing:
  # PREREQUISITES: security >= 85%, error_handling >= 80%
  enabled: true
```

Prerequisites ensure:
- Dimension has foundation to build on
- Tool has meaningful input to analyze
- Results are actionable

### Weight Adjustment for Extended Dims

When enabling extended dims, weights auto-normalize:

```
WITHOUT extended dims:
  linting: 8% → 8.8% (normalized across 9)
  ...

WITH extended dims:
  linting: 8% → 5.9% (normalized across 16)
  ...
```

Framework automatically adjusts to keep dimension importance balanced.

## References

- Mutation testing: **Stryker.js** documentation
- Property testing: **Hypothesis** + **fast-check** documentation
- Fuzzing: **libFuzzer**, **Atheris** documentation
- License compliance: **SPDX** license list
- Accessibility: **WCAG 2.1 Guidelines**
- Observability: **OpenTelemetry** standards
- Supply chain: **Sigstore** documentation

## Conclusion

Extended dimensions provide another ~15% of automation toward quality excellence. Combined with standard dimensions, the framework can reach 75-80% through automated tooling. Beyond that, human expertise becomes essential for business logic, UX, and advanced security work.
