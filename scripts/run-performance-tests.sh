#!/bin/bash
# ABOUTME: Script to run performance benchmarks
# ABOUTME: Provides various options for running performance tests

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Create Project Performance Testing ===${NC}"
echo

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Please install uv first: https://github.com/astral-sh/uv"
    exit 1
fi

# Parse command line arguments
BENCHMARK_ONLY=""
VERBOSE=""
SPECIFIC_TEST=""
COMPARE=""
SAVE_BASELINE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --benchmark-only)
            BENCHMARK_ONLY="--benchmark-only"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        --test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --compare)
            COMPARE="--benchmark-compare"
            shift
            ;;
        --save)
            SAVE_BASELINE="--benchmark-save=$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --benchmark-only    Only run benchmark tests"
            echo "  -v, --verbose       Verbose output"
            echo "  --test TEST_NAME    Run specific test"
            echo "  --compare           Compare with saved baseline"
            echo "  --save NAME         Save results as baseline NAME"
            echo "  -h, --help          Show this help message"
            echo
            echo "Examples:"
            echo "  # Run all performance tests"
            echo "  $0"
            echo
            echo "  # Run only config performance tests"
            echo "  $0 --test test_config_performance.py"
            echo
            echo "  # Save baseline results"
            echo "  $0 --save baseline"
            echo
            echo "  # Compare with baseline"
            echo "  $0 --compare"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build the pytest command
CMD="uv run pytest tests/performance/"

if [ -n "$SPECIFIC_TEST" ]; then
    CMD="$CMD$SPECIFIC_TEST"
fi

CMD="$CMD -m benchmark $VERBOSE $BENCHMARK_ONLY"

if [ -n "$SAVE_BASELINE" ]; then
    CMD="$CMD $SAVE_BASELINE"
fi

if [ -n "$COMPARE" ]; then
    CMD="$CMD $COMPARE"
fi

# Add benchmark output options
CMD="$CMD --benchmark-columns=min,max,mean,stddev,median,iqr,ops"

echo -e "${YELLOW}Running command:${NC} $CMD"
echo

# Run the tests
$CMD

echo
echo -e "${GREEN}Performance testing complete!${NC}"