# Cornflow Chart Testing

This directory contains files for testing the Cornflow Helm chart.

## Test Files

- `test-values.yaml`: Minimal values for testing (without Airflow)
- `test-values-with-airflow.yaml`: Values for testing with Airflow included
- `test.sh`: Complete automated test script
- `quick-test.sh`: Quick test script (validation only)
- `test-manifests.yaml`: Generated manifests during testing (created automatically)
- `test-manifests-with-airflow.yaml`: Manifests with Airflow (created automatically)

## How to Use

### 1. Quick Test (Validation Only)

For a quick validation without a cluster:

```bash
cd helm-charts/cornflow/tests
./quick-test.sh
```

This command:
- Validates chart syntax
- Generates templates with and without Airflow
- Shows the number of generated resources

### 2. Basic Test (Validation Only)

If you don't have a Kubernetes cluster available:

```bash
cd helm-charts/cornflow/tests
./test.sh
```

This command:
- Validates chart syntax
- Generates templates with test values
- Creates a `test-manifests.yaml` file with generated manifests

### 3. Complete Test (With Cluster)

If you have a Kubernetes cluster (minikube, kind, etc.):

```bash
cd helm-charts/cornflow/tests
./test.sh
```

This command additionally:
- Installs the chart in a test namespace
- Verifies that pods are running
- Uninstalls the chart automatically

### 4. Manual Testing

If you prefer to test step by step:

```bash
# 1. Validate syntax
helm lint ..

# 2. Generate templates with test values
helm template test-release .. -f test-values.yaml

# 3. Install in cluster (optional)
helm install test-release .. -f test-values.yaml -n cornflow-test

# 4. Verify installation
kubectl get pods -n cornflow-test

# 5. Uninstall
helm uninstall test-release -n cornflow-test
```

## Test Configuration

### test-values.yaml (Without Airflow)
- **Airflow disabled**: To simplify testing
- **Minimal resources**: Reduced CPU and memory
- **Local PostgreSQL**: Included database
- **No ingress**: For local testing
- **Basic configuration**: Only essential variables

### test-values-with-airflow.yaml (With Airflow)
- **Airflow enabled**: For complete testing
- **Minimal Airflow configuration**: Reduced resources
- **Simulated DAGs**: To avoid external dependencies
- **Same Cornflow configuration**: As the basic file

## Requirements

- Helm 3.x
- kubectl (for complete test)
- Kubernetes cluster (for complete test)

## Troubleshooting

### Error: "Cannot connect to cluster"
- Make sure you have a cluster running (minikube, kind, etc.)
- Verify that kubectl is configured correctly

### Error: "Chart has syntax errors"
- Check the templates in the `templates/` directory
- Verify YAML syntax

### Error: "Error installing chart"
- Verify that you have permissions in the cluster
- Check pod logs: `kubectl logs -n cornflow-test <pod-name>`
