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
    echo "  --rc [N]                 Mark as release candidate: appends -rc or -rc.N to chart version"
    echo "                           Image tag in values.yaml stays at the base version (e.g., release-v1.2.5)"
    echo "  -p, --package            Package chart locally"
    echo "  -u, --upload             Upload to Google Cloud Storage (requires gcloud auth)"
    echo "  -a, --all                Do everything: package and upload"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -v 1.2.5 -p              # Stable release, package only"
    echo "  $0 -v 1.2.5 -a              # Stable release, package + upload"
    echo "  $0 -v 1.2.5 --rc -p         # RC package: cornflow-1.2.5-rc.tgz"
    echo "  $0 -v 1.2.5 --rc 2 -a       # RC package: cornflow-1.2.5-rc.2.tgz"
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
# $1 = base version (e.g. 1.2.5)   — used for appVersion and image tag
# $2 = rc label (e.g. rc or rc.2)  — appended to chart version only; empty = stable
update_chart_yaml() {
    local version=$1
    local rc_label="${2:-}"

    local chart_version="$version"
    if [ -n "$rc_label" ]; then
        chart_version="${version}-${rc_label}"
    fi

    print_status "Updating Chart.yaml: version=$chart_version  appVersion=$version"

    # chart version may include rc suffix; appVersion and image tag always use the base version
    sed -i "s/^version: .*/version: $chart_version/" Chart.yaml
    sed -i "s/^appVersion: .*/appVersion: \"$version\"/" Chart.yaml
    sed -i "s/^  tag: .*/  tag: \"release-v$version\"/" values.yaml

    print_status "Updated Chart.yaml:"
    grep -E "^(version|appVersion):" Chart.yaml
    print_status "Updated image tag in values.yaml:"
    grep -E "^  tag:" values.yaml | head -1
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
    
    print_status "✅ Chart validation passed"
}

# Function to package chart
package_chart() {
    local version=$1
    print_header "Packaging Chart"
    
    # Create packages directory
    mkdir -p packages
    
    # Package the chart
    print_status "Creating chart package..."
    helm package . --destination packages/
    
    # List generated packages
    print_status "Generated packages:"
    ls -la packages/
    
    # Verify the tarball for this release only (packages/*.tgz breaks helm show with multiple files)
    local chart_tgz="packages/cornflow-${version}.tgz"
    if [ ! -f "$chart_tgz" ]; then
        print_error "Expected package not found: $chart_tgz"
        exit 1
    fi
    print_status "Verifying package..."
    helm show chart "$chart_tgz"
    
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
    
    local chart_tgz="packages/cornflow-${version}.tgz"
    if [ ! -f "$chart_tgz" ]; then
        print_error "Package not found: $chart_tgz (run with -p or -a after packaging)"
        exit 1
    fi
    
    local repo_url="https://storage.googleapis.com/cornflow-public-artifacts/"
    local index_dir
    index_dir=$(mktemp -d)

    # Download existing remote index and merge so all previous versions remain available.
    # Without --merge each release would overwrite index.yaml with only the new version.
    local existing_index="$index_dir/_existing_index.yaml"
    print_status "Fetching existing index.yaml from GCS..."
    if gsutil cp gs://cornflow-public-artifacts/index.yaml "$existing_index" 2>/dev/null; then
        print_status "Merging new version into existing index..."
        cp "$chart_tgz" "$index_dir/"
        helm repo index "$index_dir" --url "$repo_url" --merge "$existing_index"
        rm -f "$index_dir/_existing_index.yaml"
    else
        print_warning "No existing index found in GCS — creating fresh index."
        cp "$chart_tgz" "$index_dir/"
        helm repo index "$index_dir" --url "$repo_url"
    fi
    mkdir -p packages
    cp "$index_dir/index.yaml" packages/index.yaml
    rm -rf "$index_dir"
    
    # Upload only this chart version (avoid re-publishing unrelated local .tgz)
    print_status "Uploading chart package..."
    gsutil cp "$chart_tgz" gs://cornflow-public-artifacts/
    
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
    local rc_label=""
    local do_package=false
    local do_upload=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                version="$2"
                shift 2
                ;;
            --rc)
                # --rc alone → "rc"  |  --rc 2 → "rc.2"
                if [[ -n "${2:-}" && ! "${2:-}" =~ ^- ]]; then
                    rc_label="rc.${2}"
                    shift 2
                else
                    rc_label="rc"
                    shift
                fi
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
    
    # Build full chart version (base + optional rc suffix)
    local chart_version="$version"
    if [ -n "$rc_label" ]; then
        chart_version="${version}-${rc_label}"
    fi

    print_header "Cornflow Helm Chart Release v${chart_version}"

    # Validate chart first
    validate_chart

    # Update Chart.yaml (base version for image tag, full version for chart)
    update_chart_yaml "$version" "$rc_label"

    # Package chart
    if [ "$do_package" = true ]; then
        package_chart "$chart_version"
    fi

    # Upload to GCS
    if [ "$do_upload" = true ]; then
        upload_to_gcs "$chart_version"
    fi

    print_header "Release Complete"
    print_status "🎉 Successfully processed Cornflow Helm Chart v${chart_version}"
    
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
