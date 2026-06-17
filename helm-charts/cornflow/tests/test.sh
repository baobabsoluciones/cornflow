#!/bin/bash

# Simple test script for the Cornflow chart
# This script validates the chart and performs a basic installation test

set -e

echo "=== Cornflow Chart Test ==="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify we are in the correct directory
if [ ! -f "../Chart.yaml" ]; then
    print_error "Chart.yaml not found. Run this script from the helm-charts/cornflow/tests directory"
    exit 1
fi

# Verify Helm is installed
if ! command -v helm &> /dev/null; then
    print_error "Helm is not installed. Please install Helm first."
    exit 1
fi

print_status "Helm found: $(helm version --short)"

# Verify we have a Kubernetes cluster available
if ! kubectl cluster-info &> /dev/null; then
    print_warning "Cannot connect to Kubernetes cluster."
    print_warning "Make sure you have a cluster running (minikube, kind, etc.)"
    print_warning "Continuing with chart validation only..."
    SKIP_DEPLOY=true
else
    print_status "Kubernetes cluster available"
    SKIP_DEPLOY=false
fi

echo ""
print_status "1. Validating chart syntax..."

# Validate chart syntax
if helm lint ..; then
    print_status "✓ Chart valid"
else
    print_error "✗ Chart has syntax errors"
    exit 1
fi

echo ""
print_status "2. Validating templates with test values..."

# Validate templates with test values
if helm template test-release .. -f test-values.yaml > /dev/null; then
    print_status "✓ Templates generated correctly with test values"
else
    print_error "✗ Error generating templates with test values"
    exit 1
fi

echo ""
print_status "3. Generating manifests for review..."

# Generate manifests for review
helm template test-release .. -f test-values.yaml > test-manifests.yaml
print_status "✓ Manifests generated in test-manifests.yaml"

# Count generated resources
RESOURCE_COUNT=$(helm template test-release .. -f test-values.yaml | grep -c "kind:" || true)
print_status "✓ Generated $RESOURCE_COUNT Kubernetes resources"

if [ "$SKIP_DEPLOY" = false ]; then
    echo ""
    print_status "4. Installing chart in test mode..."
    
    # Create test namespace if it doesn't exist
    kubectl create namespace cornflow-test --dry-run=client -o yaml | kubectl apply -f -
    
    # Install the chart
    if helm install test-release .. -f test-values.yaml -n cornflow-test --wait --timeout=5m; then
        print_status "✓ Chart installed successfully"
        
        echo ""
        print_status "5. Verifying pod status..."
        
        # Wait for pods to be ready
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=cornflow -n cornflow-test --timeout=300s
        
        # Show pod status
        kubectl get pods -n cornflow-test
        
        echo ""
        print_status "6. Verifying services..."
        kubectl get services -n cornflow-test
        
        echo ""
        print_status "7. Uninstalling test chart..."
        
        # Uninstall the chart
        helm uninstall test-release -n cornflow-test
        
        # Clean up namespace
        kubectl delete namespace cornflow-test
        
        print_status "✓ Test completed successfully"
    else
        print_error "✗ Error installing chart"
        exit 1
    fi
else
    echo ""
    print_warning "Skipping cluster installation (not available)"
    print_status "✓ Validation test completed"
fi

echo ""
print_status "=== Test completed ==="
print_status "Generated files:"
print_status "  - test-manifests.yaml (generated manifests)"
print_status "  - test-values.yaml (test values)"

echo ""
print_status "To run a complete test, make sure you have a Kubernetes cluster available"
print_status "and run this script again."
