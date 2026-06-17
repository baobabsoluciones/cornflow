#!/bin/bash

# Cornflow Helm Chart Release Script
# This script helps prepare and release the Helm chart

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -v, --version VERSION    Chart version to release (e.g., 1.2.5)"
    echo "  -p, --package            Package chart locally"
    echo "  -u, --upload             Upload to Google Cloud Storage (requires gcloud auth)"
    echo "  -a, --all                Do everything: package and upload"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -v 1.2.5 -p          # Package chart locally"
    echo "  $0 -v 1.2.5 -u          # Upload to Google Cloud Storage"
    echo "  $0 -v 1.2.5 -a          # Complete release process"
    echo ""
    echo "Note: For automatic releases, create and push a git tag:"
    echo "  git tag helm-chart-v1.2.5 && git push origin helm-chart-v1.2.5"
    echo ""
}

# Function to validate version format
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version. Use format: X.Y.Z"
        exit 1
    fi
}



# Function to update Chart.yaml
update_chart_yaml() {
    local version=$1
    print_status "Updating Chart.yaml version to $version"
    
    # Update version in Chart.yaml
    sed -i "s/^version: .*/version: $version/" Chart.yaml
    sed -i "s/^appVersion: .*/appVersion: \"$version\"/" Chart.yaml
    
    # Update version in values.yaml if needed
    sed -i "s/^  tag: .*/  tag: \"release-v$version\"/" values.yaml
    
    print_status "Updated Chart.yaml:"
    cat Chart.yaml | grep -E "^(version|appVersion):"
}

# Function to validate chart
validate_chart() {
    print_header "Validating Chart"
    
    # Check if we're in the right directory
    if [ ! -f "Chart.yaml" ]; then
        print_error "Chart.yaml not found. Run this script from the helm-charts/cornflow directory"
        exit 1
    fi
    
    # Validate chart structure
    print_status "Running helm lint..."
    helm lint .
    
    # Update dependencies
    print_status "Updating dependencies..."
    helm dependency update
    helm dependency build
    
    # Test template rendering
    print_status "Testing template rendering..."
    helm template test-release . -f tests/test-values.yaml > /dev/null
    helm template test-release . -f tests/test-values-with-airflow.yaml > /dev/null
    
    print_status "✅ Chart validation passed"
}

# Function to package chart
package_chart() {
    print_header "Packaging Chart"
    
    # Create packages directory
    mkdir -p packages
    
    # Package the chart
    print_status "Creating chart package..."
    helm package . --destination packages/
    
    # List generated packages
    print_status "Generated packages:"
    ls -la packages/
    
    # Verify package
    print_status "Verifying package..."
    helm show chart packages/*.tgz
    
    print_status "✅ Chart packaged successfully"
}



# Function to upload to Google Cloud Storage
upload_to_gcs() {
    local version=$1
    print_header "Uploading to Google Cloud Storage"
    
    # Check if gcloud is available
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install Google Cloud SDK"
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Create index file
    print_status "Creating/updating index file..."
    gsutil cp gs://cornflow-public-artifacts/index.yaml packages/index.yaml 2>/dev/null || echo "No existing index found"
    helm repo index packages/ --url https://storage.googleapis.com/cornflow-public-artifacts/
    
    # Upload files
    print_status "Uploading chart package..."
    gsutil cp packages/*.tgz gs://cornflow-public-artifacts/
    
    print_status "Uploading index file..."
    gsutil cp packages/index.yaml gs://cornflow-public-artifacts/
    
    # Make files publicly readable
    print_status "Setting public permissions..."
    gsutil iam ch allUsers:objectViewer gs://cornflow-public-artifacts/
    
    # Verify upload
    print_status "Verifying upload..."
    gsutil ls gs://cornflow-public-artifacts/
    
    print_status "✅ Chart uploaded successfully"
    print_status "Repository URL: https://storage.googleapis.com/cornflow-public-artifacts/"
    print_status "Install with: helm repo add cornflow https://storage.googleapis.com/cornflow-public-artifacts/"
}

# Main script logic
main() {
    local version=""
    local do_package=false
    local do_upload=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                version="$2"
                shift 2
                ;;
            -p|--package)
                do_package=true
                shift
                ;;
            -u|--upload)
                do_upload=true
                shift
                ;;
            -a|--all)
                do_package=true
                do_upload=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check if version is provided
    if [ -z "$version" ]; then
        print_error "Version is required. Use -v or --version"
        show_usage
        exit 1
    fi
    
    # Validate version format
    validate_version "$version"
    
    print_header "Cornflow Helm Chart Release v$version"
    
    # Validate chart first
    validate_chart
    
    # Update Chart.yaml
    update_chart_yaml "$version"
    
    # Package chart
    if [ "$do_package" = true ]; then
        package_chart
    fi
    
    # Upload to GCS
    if [ "$do_upload" = true ]; then
        upload_to_gcs "$version"
    fi
    
    print_header "Release Complete"
    print_status "🎉 Successfully processed Cornflow Helm Chart v$version"
    
    if [ "$do_upload" = true ]; then
        echo ""
        print_status "Next steps:"
        print_status "1. Test the release: helm repo add cornflow https://storage.googleapis.com/cornflow-public-artifacts/"
        print_status "2. Install: helm install my-cornflow cornflow/cornflow"
        print_status "3. Update documentation if needed"
    fi
}

# Run main function with all arguments
main "$@"
