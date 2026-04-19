#!/bin/bash
# Install Extended Dimensions Tools
# Usage: ./scripts/install_extended_tools.sh [--high|--medium|--low|--all]

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

install_high() {
    echo; log_info "=== Mutation Testing (HIGH) ==="
    log_info "Installing mutmut...";   pip3 install mutmut  2>/dev/null || log_error "mutmut failed"
    log_info "Installing stryker...";  npm install -g stryker stryker-cli 2>/dev/null || log_error "stryker failed"
    check_tool "mutmut"  "pip3" || log_error "mutmut verification failed"
    check_tool "stryker" "npm"  || log_error "stryker verification failed"
}

install_medium() {
    echo; log_info "=== Property Testing, Fuzzing, Accessibility (MEDIUM) ==="
    log_info "Installing hypothesis...";  pip3 install hypothesis  2>/dev/null || log_error "hypothesis failed"
    log_info "Installing fast-check..."; npm install -g fast-check 2>/dev/null || log_error "fast-check failed"
    log_info "Installing pa11y...";     npm install -g pa11y axe-core 2>/dev/null || log_error "pa11y failed"
    check_tool "hypothesis" "pip3" || log_error "hypothesis verification failed"
    check_tool "fast-check" "npm"  || log_error "fast-check verification failed"
    check_tool "pa11y"     "npm"  || log_error "pa11y verification failed"
}

install_low() {
    echo; log_info "=== License, Observability, Supply Chain (LOW) ==="
    log_info "Installing scancode..."; pip3 install scancode-toolkit 2>/dev/null || log_error "scancode failed"
    check_tool "scancode" "pip3" || log_error "scancode verification failed"
}

verify_all() {
    echo; log_info "=== Verification ==="
    echo "pip3:  mutmut hypothesis scancode"
    for t in mutmut hypothesis scancode; do check_tool "$t" "pip3" || log_error "$t not installed"; done
    echo "npm:   stryker fast-check pa11y"
    for t in stryker fast-check pa11y; do check_tool "$t" "npm" || log_error "$t not installed"; done
    echo "brew:  syft grype (optional, macOS)"
    for t in syft grype; do check_tool "$t" "brew" || log_warn "$t not installed (optional)"; done
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
echo; log_ok "Done. Enable extended dims in config.advanced.yaml."
