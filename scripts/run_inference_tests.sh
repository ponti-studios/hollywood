#!/bin/bash
#
# run_inference_tests.sh — Execute all Gemma 4 tool-calling inference tests
#
# This script:
#   1. Validates prerequisites (MLX stack, model cache)
#   2. Runs all 9 inference tests
#   3. Logs results to .data/api/inference.db
#   4. Generates a summary report
#
# Usage:
#   ./scripts/run_inference_tests.sh
#   ./scripts/run_inference_tests.sh --model mlx-community/gemma-4-e2b-bf16
#   ./scripts/run_inference_tests.sh --verbose
#   ./scripts/run_inference_tests.sh --quick  # Single test only
#
# Environment:
#   INFERENCE_DB: Path to inference database (default: .data/api/inference.db)
#   MODEL_ID: Gemma model to test (default: mlx-community/gemma-4-e2b-bf16)
#

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

INFERENCE_DB="${INFERENCE_DB:-.data/api/inference.db}"
MODEL_ID="${MODEL_ID:-mlx-community/gemma-4-e2b-bf16}"
VERBOSE="${VERBOSE:-false}"
QUICK_TEST="${QUICK_TEST:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" >&2
}

log_section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Validation Functions
# ─────────────────────────────────────────────────────────────────────────────

check_python() {
    log_info "Checking Python environment..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.12+"
        return 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Python $PYTHON_VERSION found"
}

check_uv() {
    log_info "Checking uv package manager..."

    if ! command -v uv &> /dev/null; then
        log_error "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi

    log_success "uv is installed"
}

check_mlx_vlm() {
    log_info "Checking mlx-vlm installation..."

    if ! python3 -c "import mlx_vlm" 2>/dev/null; then
        log_warn "mlx-vlm not installed"
        log_info "Installing MLX stack..."
        cd "$PROJECT_ROOT"
        if ! uv pip install mlx mlx-lm mlx-vlm 2>&1 | tail -5; then
            log_error "Failed to install mlx-vlm"
            return 1
        fi
    fi

    log_success "mlx-vlm is installed"
}

check_model_cache() {
    log_info "Checking model cache..."

    if ! python3 -c "from mlx_vlm import load; load('$MODEL_ID')" 2>&1 | grep -q "Downloading\|Fetching"; then
        log_success "Model already cached"
        return 0
    fi

    log_info "Downloading model (this may take 5-10 minutes)..."
    if python3 -c "from mlx_vlm import load; load('$MODEL_ID')" 2>&1 | tail -3; then
        log_success "Model download complete"
    else
        log_error "Failed to download model"
        return 1
    fi
}

check_test_file() {
    log_info "Checking test file..."

    if [ ! -f "$PROJECT_ROOT/tests/test_tool_calls.py" ]; then
        log_error "Test file not found: tests/test_tool_calls.py"
        return 1
    fi

    # Verify syntax
    if ! python3 -m py_compile "$PROJECT_ROOT/tests/test_tool_calls.py" 2>/dev/null; then
        log_error "Test file has syntax errors"
        return 1
    fi

    log_success "Test file is valid"
}

# ─────────────────────────────────────────────────────────────────────────────
# Test Execution Functions
# ─────────────────────────────────────────────────────────────────────────────

run_single_test() {
    local test_path="$1"
    local test_name=$(basename "$test_path" | cut -d':' -f3)

    log_info "Running: $test_name"

    cd "$PROJECT_ROOT"

    # Run with verbose output if requested
    if [ "$VERBOSE" = "true" ]; then
        uv run pytest "$test_path" -v -s --run-inference --model "$MODEL_ID" 2>&1
    else
        uv run pytest "$test_path" -v --run-inference --model "$MODEL_ID" 2>&1 | tail -20
    fi
}

run_all_tests() {
    log_section "RUNNING ALL INFERENCE TESTS"

    cd "$PROJECT_ROOT"

    log_info "Model: $MODEL_ID"
    log_info "Database: $INFERENCE_DB"
    log_info "Verbose: $VERBOSE"
    echo ""

    # Run all tests
    if [ "$VERBOSE" = "true" ]; then
        uv run pytest tests/test_tool_calls.py -v -s --run-inference --model "$MODEL_ID"
    else
        uv run pytest tests/test_tool_calls.py -v --run-inference --model "$MODEL_ID"
    fi
}

run_quick_test() {
    log_section "RUNNING QUICK SMOKE TEST"

    cd "$PROJECT_ROOT"

    log_info "Running single test for validation..."
    log_info "Model: $MODEL_ID"
    echo ""

    uv run pytest \
        "tests/test_tool_calls.py::TestToolCallDetection::test_calculate_multiplication" \
        -v -s --run-inference --model "$MODEL_ID"
}

# ─────────────────────────────────────────────────────────────────────────────
# Analysis Functions
# ─────────────────────────────────────────────────────────────────────────────

analyze_results() {
    if [ ! -f "$INFERENCE_DB" ]; then
        log_warn "No inference database found. Tests may not have been run."
        return 0
    fi

    log_section "TEST RESULTS ANALYSIS"

    cd "$PROJECT_ROOT"
    python3 scripts/analyze_inference_runs.py --db "$INFERENCE_DB" --limit 100
}

generate_report() {
    log_section "GENERATING TEST REPORT"

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="$PROJECT_ROOT/.data/reports/inference_report_$(date +%s).txt"

    mkdir -p "$(dirname "$report_file")"

    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "GEMMA 4 INFERENCE TEST REPORT"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "Timestamp: $timestamp"
        echo "Model: $MODEL_ID"
        echo "Database: $INFERENCE_DB"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo ""

        if [ -f "$INFERENCE_DB" ]; then
            python3 scripts/analyze_inference_runs.py --db "$INFERENCE_DB" --limit 100
        else
            echo "No database found."
        fi
    } | tee "$report_file"

    log_success "Report saved to: $report_file"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                MODEL_ID="$2"
                shift 2
                ;;
            --db)
                INFERENCE_DB="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --quick)
                QUICK_TEST=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --model MODEL_ID       Model to test (default: mlx-community/gemma-4-e2b-bf16)"
                echo "  --db PATH              Database path (default: .data/api/inference.db)"
                echo "  --verbose              Show full pytest output"
                echo "  --quick                Run single smoke test only"
                echo "  --help                 Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0"
                echo "  $0 --verbose"
                echo "  $0 --quick"
                echo "  $0 --model mlx-community/gemma-4-e2b-bf16 --verbose"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    log_section "GEMMA 4 INFERENCE TEST RUNNER"

    # Validate prerequisites
    log_section "VALIDATING PREREQUISITES"

    check_python || exit 1
    check_uv || exit 1
    check_mlx_vlm || exit 1
    check_test_file || exit 1
    check_model_cache || exit 1

    log_success "All prerequisites validated"

    # Run tests
    if [ "$QUICK_TEST" = "true" ]; then
        run_quick_test || {
            log_error "Quick test failed"
            exit 1
        }
    else
        run_all_tests || {
            log_error "Test suite failed"
            exit 1
        }
    fi

    # Analyze results
    sleep 1
    analyze_results

    # Generate report
    generate_report

    log_section "TEST RUN COMPLETE"
    log_success "All tests completed successfully!"
    log_info "Results saved to: $INFERENCE_DB"
    log_info "Report saved to: .data/reports/"
}

# Run main function
main "$@"
