#!/bin/bash

# X-Y Table Control System Test Runner
# This script runs all tests in the project with proper Python path setup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

print_status "Running tests from: $PROJECT_ROOT"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
print_status "Using $PYTHON_VERSION"

# Check if pytest is available
if ! python3 -c "import pytest" 2>/dev/null; then
    print_warning "pytest not found. Installing pytest..."
    pip3 install pytest
fi

# Set up Python path to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
print_status "PYTHONPATH set to: $PYTHONPATH"

# Check for test files
TEST_FILES=$(find tests -name "test_*.py" -type f)
if [ -z "$TEST_FILES" ]; then
    print_error "No test files found in tests directory"
    exit 1
fi

print_status "Found test files:"
for test_file in $TEST_FILES; do
    echo "  - $test_file"
done

# Run tests with verbose output and coverage
print_status "Running all tests..."
echo "=================================="

# Run pytest with verbose output, show local variables on failures, and stop on first failure
python3 -m pytest tests/ \
    -v \
    --tb=short \
    --maxfail=1 \
    --color=yes \
    --durations=10

# Capture the exit code
TEST_EXIT_CODE=$?

echo "=================================="

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "All tests passed!"
    echo ""
    print_status "Test Summary:"
    echo "  - All test files executed successfully"
    echo "  - No failures detected"
    echo "  - System is ready for deployment"
else
    print_error "Some tests failed!"
    echo ""
    print_status "Test Summary:"
    echo "  - Test execution completed with failures"
    echo "  - Please review the output above for details"
    echo "  - Fix failing tests before deployment"
fi

# Optional: Run with coverage if available
if python3 -c "import coverage" 2>/dev/null; then
    print_status "Running tests with coverage report..."
    python3 -m coverage run -m pytest tests/ -v
    python3 -m coverage report --show-missing > /dev/null 2>&1
    python3 -m coverage html
    print_status "Coverage report generated in htmlcov/index.html"
elif command -v pip3 &> /dev/null; then
    print_warning "coverage not installed. Install with: pip3 install coverage"
fi

exit $TEST_EXIT_CODE 