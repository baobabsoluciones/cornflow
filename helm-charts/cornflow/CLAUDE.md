# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Helm 3 chart** for deploying [Cornflow](https://github.com/baobabsoluciones/cornflow) — an open-source optimization platform — to Kubernetes. The chart is published to a public GCS-backed Helm repository at `https://storage.googleapis.com/cornflow-public-artifacts/`.

## Common Commands

### Chart validation and rendering

```bash
helm lint .
helm dependency update        # fetch/refresh subchart (Airflow)
helm dependency build
helm template test-release . -f values.yaml   # render all templates locally
```

### Install / upgrade

```bash
# From local directory
helm install my-project ./cornflow

# From public repo
helm repo add cornflow https://storage.googleapis.com/cornflow-public-artifacts/
helm install my-cornflow cornflow/cornflow
```

### Release workflow

```bash
# Package only
./scripts/release.sh -v 1.2.5 -p

# Upload to GCS only
./scripts/release.sh -v 1.2.5 -u

# Full release (package + upload + index update)
./scripts/release.sh -v 1.2.5 -a
```

The release script also updates the version in `Chart.yaml` and `values.yaml`.

## Architecture

### Components

| Component | Kubernetes resource | Notes |
|---|---|---|
| Cornflow API | `Deployment` | Flask app, port 5000, health at `/health/` |
| Cornflow PostgreSQL | `Deployment` | Port 5432, named `{release}-cornflow-postgresql` |
| Airflow (optional) | subchart | Apache Airflow ~1.16.0, KubernetesExecutor |
| Airflow PostgreSQL | `Deployment` | Separate DB, named `{release}-postgresql` |

### Template helpers (`templates/_helpers.tpl`)

All resource names are derived from the release name to allow multiple installs in the same cluster. Use the defined helpers rather than hard-coding names.

### Airflow integration

Airflow is an optional dependency controlled by `airflow.enabled` in `values.yaml`. When enabled:

- Two init containers run before the scheduler/webserver: one clones `baobabsoluciones/cornflow` from GitHub, the second runs `pip install` into `/opt/airflow/dags/deps`.
- A PVC (`airflow-dags-pvc.yaml`) holds the DAG files.
- The release name must be manually set in `values.yaml` under `airflow.config.AIRFLOW__KUBERNETES__NAMESPACE` and related keys because the Airflow subchart cannot self-reference the Helm release name.
- Airflow uses a `ClusterRole` (not `Role`) so the KubernetesExecutor can spawn worker pods.

### Dual PostgreSQL strategy

The chart embeds its own PostgreSQL deployments rather than using a Bitnami subchart:
- **Cornflow DB**: `{release}-cornflow-postgresql` — holds application data.
- **Airflow DB**: `{release}-postgresql` — holds Airflow metadata. Kept separate to avoid migration conflicts.

### Security posture

- Non-root containers (`runAsUser: 1000`), read-only root filesystems.
- Cornflow has a `Role`/`RoleBinding`; Airflow has a `ClusterRole`/`ClusterRoleBinding`.
- Authentication supports: DB (default), LDAP (with group→role mapping), OpenID Connect.

## Key Files

- `Chart.yaml` — chart version and Airflow dependency declaration.
- `values.yaml` — all tuneable parameters; ~50 Cornflow env vars, Airflow config, resource limits, autoscaling, ingress.
- `templates/cornflow-deployment.yaml` — main Cornflow pod spec.
- `templates/configmaps.yaml` — ConfigMap that injects env vars into the pod.
- `scripts/release.sh` — release automation; handles version bumps, packaging, GCS upload, and index regeneration (always overwrites `index.yaml`, no merge).

## Publishing

Releases are triggered by pushing a git tag (`helm-chart-vX.Y.Z`). A GitHub Action packages the chart, uploads it to `gs://cornflow-public-artifacts/`, and creates a GitHub release. The index.yaml in the repo root is the Helm repository index.
