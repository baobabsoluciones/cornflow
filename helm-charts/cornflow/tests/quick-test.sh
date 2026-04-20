#!/bin/bash

# Quick test for the Cornflow chart
# Only validates syntax and generates templates

set -e

echo "=== Quick Test of Cornflow Chart ==="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify we are in the correct directory
if [ ! -f "../Chart.yaml" ]; then
    print_error "Chart.yaml not found. Run from helm-charts/cornflow/tests"
    exit 1
fi

# Test 1: Validate syntax
echo "1. Validating syntax..."
if helm lint .. > /dev/null 2>&1; then
    print_status "Valid syntax"
else
    print_error "Syntax errors found"
    helm lint ..
    exit 1
fi

# Test 2: Generate templates without Airflow
echo "2. Generating templates without Airflow..."
if helm template test-release .. -f test-values.yaml > /dev/null 2>&1; then
    RESOURCES=$(helm template test-release .. -f test-values.yaml | grep -c "kind:" || echo "0")
    print_status "Templates without Airflow: $RESOURCES resources"
else
    print_error "Error generating templates without Airflow"
    exit 1
fi

# Test 3: Generate templates with Airflow
echo "3. Generating templates with Airflow..."
if helm template test-release .. -f test-values-with-airflow.yaml > /dev/null 2>&1; then
    RESOURCES=$(helm template test-release .. -f test-values-with-airflow.yaml | grep -c "kind:" || echo "0")
    print_status "Templates with Airflow: $RESOURCES resources"
else
    print_error "Error generating templates with Airflow"
    exit 1
fi

echo ""
print_status "Quick test completed successfully"
print_status "The chart is ready to use"
