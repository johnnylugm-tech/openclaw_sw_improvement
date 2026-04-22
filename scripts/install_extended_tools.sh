#!/bin/bash
# Install Extended Dimensions Tools
# Usage: ./scripts/install_extended_tools.sh [--high|--medium|--low|--all]
#
# NOTE: mutation_testing is a CORE dimension (not extended).
# It uses pytest-gremlins (pytest plugin), NOT mutmut.
# Core tools are verified via: python3 scripts/verify_tools.py
#
# This script installs tools for EXTENDED dimensions only:
#   --high:   property_testing (hypothesis)
#   --medium: fuzzing (athena/atheris), accessibility (pa11y, axe-core)
#   --low:    observability (syft, grype), supply_chain_security (cosign)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}i${NC} $1"; }
log_warn()  { echo -e "${YELLOW}!${NC} $1"; }
log_error() { echo -e "${RED}x${NC} $1"; }
log_ok()    { echo -e "${GREEN}v${NC} $1"; }

check_tool() {
    local tool=$1
    local manager=$2
    case $manager in
        pip3)
            if pip3 show "$tool" &>/dev/null 2>&1; then
                local version=$(pip3 show "$tool" 2>/dev/null | grep "^Version:" | awk '{print $2}')
                log_ok "$tool v$version"; return 0; fi ;;
        npm)
            if npm list -g "$tool" &>/dev/null 2>&1; then
                log_ok "$tool installed"; return 0; fi ;;
        brew)
            if brew list "$tool" &>/dev/null 2>&1; then
                local version=$(brew list --versions "$tool" 2>/dev/null | awk '{print $NF}')
                log_ok "$tool v$version"; return 0; fi ;;
    esac
    return 1
}

log_core_required() {
    echo; log_info "=== Core: pytest-gremlins for mutation_testing ==="
    log_info "mutation_testing is a CORE dimension — install via:"
    log_info "  pip install pytest-gremlins"
    log_info "Verified via: python3 scripts/verify_tools.py"
    echo
}

install_high() {
    # Property testing (hypothesis is Python-only, fast-check is JS)
    echo; log_info "=== Property Testing (HIGH) ==="
    log_info "Installing hypothesis...";  pip3 install hypothesis  2>/dev/null || log_error "hypothesis failed"
    log_info "Installing fast-check..."; npm install -g fast-check 2>/dev/null || log_warn "fast-check failed (optional)"
    check_tool "hypothesis" "pip3" || log_error "hypothesis verification failed"
}

install_medium() {
    # Fuzzing + Accessibility
    echo; log_info "=== Fuzzing + Accessibility (MEDIUM) ==="
    log_info "Installing atheris (fuzzing)..."; pip3 install atheris 2>/dev/null || log_warn "atheris failed (Python 3.9+ required)"
    log_info "Installing pa11y..."; npm install -g pa11y 2>/dev/null || log_warn "pa11y failed (optional)"
    log_info "Installing axe-core..."; npm install -g axe-core 2>/dev/null || log_warn "axe-core failed (optional)"
    check_tool "atheris" "pip3" || log_warn "atheris not installed (optional)"
}

install_low() {
    # Observability + Supply Chain
    echo; log_info "=== Observability + Supply Chain (LOW) ==="
    log_info "Installing syft...";  brew install syft 2>/dev/null || log_warn "syft failed (optional)"
    log_info "Installing grype..."; brew install grype 2>/dev/null || log_warn "grype failed (optional)"
    log_info "Installing cosign..."; brew install cosign 2>/dev/null || log_warn "cosign failed (optional)"
    check_tool "syft"   "brew" || log_warn "syft not installed (optional)"
    check_tool "grype"  "brew" || log_warn "grype not installed (optional)"
    check_tool "cosign" "brew" || log_warn "cosign not installed (optional)"
}

verify_all() {
    echo; log_info "=== Verification ==="
    echo "pip3:  hypothesis"
    check_tool "hypothesis" "pip3" || log_warn "hypothesis not installed"
    echo "npm:   fast-check pa11y axe-core"
    for t in fast-check pa11y axe-core; do
        check_tool "$t" "npm" || log_warn "$t not installed (optional)"
    done
    echo "brew:  syft grype cosign"
    for t in syft grype cosign; do
        check_tool "$t" "brew" || log_warn "$t not installed (optional)"
    done
}

PRIORITY="${1:-all}"
case $PRIORITY in
    --high)   install_high ;;
    --medium) install_medium ;;
    --low)    install_low ;;
    --all)    install_high; install_medium; install_low ;;
    *)        echo "Usage: $0 [--high|--medium|--low|--all]"; exit 1 ;;
esac

verify_all
log_core_required
echo; log_ok "Done. Enable extended dims in config.advanced.yaml."
echo "NOTE: Core tools (pytest-gremlins, pyright, pylint, etc.) are verified via:"
echo "  python3 scripts/verify_tools.py"
