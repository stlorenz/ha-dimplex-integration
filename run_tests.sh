#!/bin/bash
# Test runner script for Dimplex integration

set -e

echo "===================="
echo "Dimplex Integration Test Suite"
echo "===================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements_test.txt

echo ""
echo "===================="
echo "Running Tests"
echo "===================="
echo ""

# Run pytest with coverage
pytest tests/ -v

echo ""
echo "===================="
echo "Test Results"
echo "===================="
echo ""
echo "Coverage report available in htmlcov/index.html"
echo ""

