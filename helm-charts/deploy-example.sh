#!/bin/bash

# Example script to deploy Cornflow using Helm
# Usage: ./deploy-example.sh [namespace] [release-name]

set -e

# Default configuration
NAMESPACE=${1:-cornflow}
RELEASE_NAME=${2:-my-cornflow}

echo "🚀 Deploying Cornflow to Kubernetes..."
echo "Namespace: $NAMESPACE"
echo "Release name: $RELEASE_NAME"

# Check if Helm is installed
if ! command -v helm &> /dev/null; then
    echo "❌ Helm is not installed. Please install Helm first."
    exit 1
fi

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or there's no access to the cluster."
    exit 1
fi

# Create namespace if it doesn't exist
echo "📦 Creating namespace '$NAMESPACE'..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create custom overrides for deployment
cat > /tmp/cornflow-overrides.yaml << EOF
# Custom overrides for example deployment
cornflow:
  env:
    SECRET_KEY: "example-secret-key-change-in-production"
    CORNFLOW_ADMIN_PWD: "admin123"
    CORNFLOW_SERVICE_PWD: "service123"
  
  # Resource configuration for development
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi

EOF

# Install the chart
echo "📥 Installing Cornflow chart..."
helm install $RELEASE_NAME ./cornflow \
    --namespace $NAMESPACE \
    --values values-cornflow.yaml \
    --values /tmp/cornflow-overrides.yaml \
    --wait \
    --timeout 10m

# Clean up temporary file
rm -f /tmp/cornflow-overrides.yaml

echo "✅ Deployment completed!"
echo ""
echo "📋 Deployment information:"
echo "   Namespace: $NAMESPACE"
echo "   Release: $RELEASE_NAME"
echo ""
echo "🔍 Checking deployment status..."
kubectl get all -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME

echo ""
echo "🌐 To access Cornflow:"
echo "   kubectl port-forward svc/$RELEASE_NAME-cornflow 5000:5000 -n $NAMESPACE"
echo "   Then open http://localhost:5000 in your browser"
echo ""
echo "📊 To view logs:"
echo "   kubectl logs -f deployment/$RELEASE_NAME-cornflow -n $NAMESPACE"
echo ""
echo "🗑️  To uninstall:"
echo "   helm uninstall $RELEASE_NAME -n $NAMESPACE"
echo "   kubectl delete namespace $NAMESPACE" 