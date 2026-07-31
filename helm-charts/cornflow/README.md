# Cornflow Helm Chart

This Helm chart deploys [Cornflow](https://github.com/baobabsoluciones/cornflow), an open-source optimization platform, to a Kubernetes cluster.

## Description

Cornflow is a platform that allows you to create, execute, and manage optimization problems easily and scalably. This chart includes:

- **Cornflow API**: Main application service
- **PostgreSQL**: Database for Cornflow
- **Airflow** (optional): Apache Airflow for workflow orchestration
- **Ingress**: Optional configuration for external access

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- A configured Kubernetes cluster
- An Ingress controller (optional, for external access)

## Installation

### Basic Installation

```bash
# Add the repository
helm repo add cornflow https://storage.googleapis.com/cornflow-public-artifacts/
helm repo update

# Install the chart
helm install my-project cornflow/cornflow
```

### Installation from Local Directory

```bash
# From the chart directory
helm install my-project ./helm-charts/cornflow
```

### Installation with Different Release Names

The chart is parameterized to work with different release names. You can install it as:

```bash
# Installation with release name "cornflow"
helm install cornflow ./helm-charts/cornflow

# Installation with release name "cornflow-staging"
helm install cornflow-staging ./helm-charts/cornflow

# Installation with release name "my-cornflow"
helm install my-cornflow ./helm-charts/cornflow
```

**IMPORTANT:** If you use a release name different from "my-cornflow", you need to manually modify the following variables in `values.yaml`:

1. **In the `cornflow.env` section:**
   ```yaml
   CORNFLOW_DB_HOST: Automatically configured (no manual change needed)
   AIRFLOW_URL: Automatically configured (no manual change needed)
   ```

2. **In the `airflow.extraVolumes` section:**
   ```yaml
   claimName: RELEASE_NAME-airflow-dags
   ```
   Change `RELEASE_NAME` to your release name

3. **In the `airflow.env` section:**
   ```yaml
   AIRFLOW_CONN_CF_URI: This must be configured manually
   ```
   The URL must be configured based on the `EXTERNAL_APP` setting in `cornflow.env`:
   - If `EXTERNAL_APP=0`: `http://service_user:Service_user1234@RELEASE_NAME-cornflow-server:5000/`
   - If `EXTERNAL_APP=1`: `http://service_user:Service_user1234@RELEASE_NAME-cornflow-server:5000/cornflow/`

**Examples:**

For release "cornflow":
```yaml
# CORNFLOW_DB_HOST: Automatically configured as "cornflow-cornflow-postgresql"
# AIRFLOW_URL: Automatically configured as "http://cornflow-webserver:8080"
claimName: cornflow-airflow-dags
AIRFLOW_CONN_CF_URI: "http://service_user:Service_user1234@cornflow-cornflow-server:5000/"
```

For release "cornflow-staging":
```yaml
# CORNFLOW_DB_HOST: Automatically configured as "cornflow-staging-cornflow-postgresql"
# AIRFLOW_URL: Automatically configured as "http://cornflow-staging-webserver:8080"
claimName: cornflow-staging-airflow-dags
AIRFLOW_CONN_CF_URI: "http://service_user:Service_user1234@cornflow-staging-cornflow-server:5000/"
```

For release "my-project":
```yaml
# CORNFLOW_DB_HOST: Automatically configured as "my-project-cornflow-postgresql"
# AIRFLOW_URL: Automatically configured as "http://my-project-webserver:8080"
claimName: my-project-airflow-dags
AIRFLOW_CONN_CF_URI: "http://service_user:Service_user1234@my-project-cornflow-server:5000/"
```

### Installation with Custom Values

```bash
# Install with the default values file
helm install my-project ./helm-charts/cornflow

# Or create a custom values file with your overrides
cat > my-overrides.yaml << EOF
cornflow:
  env:
    SECRET_KEY: "my-very-secure-secret-key"
    CORNFLOW_ADMIN_PWD: "my-admin-password"
    CORNFLOW_SERVICE_PWD: "my-service-password"

ingress:
  enabled: true
  hosts:
    - host: cornflow.mydomain.com
      paths:
        - path: /
          pathType: Prefix

# Enable Airflow
airflow:
  enabled: true
  users:
    - username: admin
      password: "my-airflow-password"
      email: admin@example.com
      firstName: admin
      lastName: admin
      role: Admin
EOF

# Install with custom overrides
helm install my-project ./helm-charts/cornflow -f my-overrides.yaml
```

### Installation with Airflow

```bash
# Enable Airflow in the values.yaml file and install
# Edit values.yaml and set airflow.enabled: true
helm install my-project ./helm-charts/cornflow

# Or enable Airflow manually during installation
helm install my-project ./helm-charts/cornflow --set airflow.enabled=true

# Install with custom Airflow configuration
helm install my-project ./helm-charts/cornflow \
  --set airflow.enabled=true \
  --set airflow.users[0].password=my-secure-password \
  --set airflow.postgresql.auth.password=my-db-password
```

**Note:** Airflow uses its own PostgreSQL database, separate from Cornflow's database. This simplifies the configuration and avoids potential conflicts. Each service has unique names:
- Cornflow PostgreSQL: `my-project-cornflow-postgresql`
- Airflow PostgreSQL: `my-project-postgresql`

## Configuration

### Main Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `image.repository` | Cornflow image repository | `baobabsoluciones/cornflow` |
| `image.tag` | Cornflow image tag | `release-v1.2.3` |
| `cornflow.replicaCount` | Number of Cornflow replicas | `1` |
| `postgresql.enabled` | Enable PostgreSQL for Cornflow | `true` |
| `airflow.enabled` | Enable Airflow deployment | `false` |
| `ingress.enabled` | Enable Ingress for Cornflow | `false` |

### Database Configuration

The chart deploys separate PostgreSQL databases for Cornflow and Airflow to avoid conflicts:

#### Cornflow Database

```yaml
postgresql:
  enabled: true
  auth:
    username: "cornflow"
    password: "cornflow"
    database: "cornflow"
  primary:
    persistence:
      enabled: true
      size: 8Gi
```

#### Airflow Database

```yaml
airflowPostgresql:
  enabled: true
  auth:
    username: "airflow"
    password: "airflow"
    database: "airflow"
  primary:
    persistence:
      enabled: true
      size: 8Gi
```

**Important:** The chart automatically disables Airflow's built-in PostgreSQL to prevent conflicts. Each database has unique service names:
- Cornflow: `my-project-cornflow-postgresql`
- Airflow: `my-project-postgresql`

### External App Configuration

The chart supports running Cornflow as an external application with a specific URL path. This is controlled by the `EXTERNAL_APP` environment variable:

```yaml
cornflow:
  env:
    EXTERNAL_APP: "0"  # Set to "1" if running as external app
```

**When `EXTERNAL_APP=0` (default):**
- Cornflow runs at the root URL: `http://my-project-cornflow-server:5000/`
- Airflow connects to: `http://service_user:Service_user1234@my-project-cornflow-server:5000/`

**When `EXTERNAL_APP=1`:**
- Cornflow runs at a specific path: `http://my-project-cornflow-server:5000/cornflow/`
- Airflow connects to: `http://service_user:Service_user1234@my-project-cornflow-server:5000/cornflow/`

### Airflow Configuration

To enable Airflow, simply set `airflow.enabled: true` in your values file:

```yaml
# Enable Airflow deployment
airflow:
  enabled: true
  
  # Airflow image (Baobab Soluciones)
  image:
    repository: baobabsoluciones/airflow
    tag: "release-v1.2.3"
    pullPolicy: IfNotPresent
  
  # Airflow users
  users:
    - username: admin
      password: admin123  # CHANGE THIS FOR PRODUCTION
      email: admin@example.com
      firstName: admin
      lastName: admin
      role: Admin
  
  # Airflow webserver configuration
  webserver:
    replicaCount: 1
    service:
      type: ClusterIP
      port: 8080
  
  # Airflow scheduler configuration
  scheduler:
    replicaCount: 1
  
  # Airflow database configuration (separate from Cornflow's database)
  # This is configured in the airflowPostgresql section
  # The chart automatically disables Airflow's built-in PostgreSQL to avoid conflicts
  
  # Airflow uses KubernetesExecutor (no Redis needed)
  # Each task runs in its own Kubernetes pod for better isolation and scalability
  # RBAC permissions are automatically configured for pod creation
```

**Important:** When Airflow is enabled, Cornflow will automatically be configured to connect to it. Make sure the `AIRFLOW_USER` and `AIRFLOW_PWD` in the Cornflow configuration match the Airflow `users[0].username` and `users[0].password`.

### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: cornflow.mydomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: cornflow-tls
      hosts:
        - cornflow.mydomain.com
```

### Resource Configuration

```yaml
cornflow:
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi

airflow:
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi
```

### Persistence Configuration

```yaml
persistence:
  enabled: true
  storageClass: "fast-ssd"
  size: 10Gi
  accessMode: ReadWriteOnce
```

## Environment Variables

### Core Application Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `DATABASE_URL` | Database connection string | `postgresql://cornflow:cornflow@cornflow-postgresql:5432/cornflow` |
| `SERVICE_NAME` | Application service name | `Cornflow` |
| `SECRET_KEY` | Application secret key | `your-secret-key-here` |
| `SECRET_BI_KEY` | BI secret key | `your-bi-secret-key-here` |
| `AUTH_TYPE` | Authentication type (1=DB, 2=OID) | `1` |
| `DEFAULT_ROLE` | Default user role | `2` (Planner) |
| `CORS_ORIGINS` | CORS allowed origins | `*` |
| `LOG_LEVEL` | Log level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR) | `20` |
| `SIGNUP_ACTIVATED` | Enable user signup | `1` |
| `CORNFLOW_SERVICE_USER` | Service user name | `service_user` |
| `SERVICE_USER_ALLOW_PASSWORD_LOGIN` | Allow service user password login | `1` |
| `OPEN_DEPLOYMENT` | Open deployment mode | `1` |
| `USER_ACCESS_ALL_OBJECTS` | Planner access to other users' objects | `0` |
| `TOKEN_DURATION` | Token duration in hours | `24` |
| `PWD_ROTATION_TIME` | Password rotation time in days | `120` |

### Authentication Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `CORNFLOW_ADMIN_USER` | Admin user | `cornflow_admin` |
| `CORNFLOW_ADMIN_PWD` | Admin password | `Cornflow_admin1234` |
| `CORNFLOW_SERVICE_PWD` | Service user password | `Service_user1234` |

### LDAP Configuration (for LDAP authentication)

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `LDAP_HOST` | LDAP server URL | `ldap://openldap:389` |
| `LDAP_BIND_DN` | LDAP bind DN | `cn=admin,dc=example,dc=org` |
| `LDAP_BIND_PASSWORD` | LDAP bind password | `admin` |
| `LDAP_USERNAME_ATTRIBUTE` | Username attribute | `cn` |
| `LDAP_USER_BASE` | User base DN | `ou=users,dc=example,dc=org` |
| `LDAP_EMAIL_ATTRIBUTE` | Email attribute | `mail` |
| `LDAP_GROUP_ATTRIBUTE` | Group attribute | `cn` |
| `LDAP_GROUP_BASE` | Group base DN | `dc=example,dc=org` |

### OpenID Connect Configuration (for OID authentication)

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `OID_PROVIDER` | OpenID provider URL | `` |
| `OID_EXPECTED_AUDIENCE` | Expected audience | `` |

### Email Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `SERVICE_EMAIL_ADDRESS` | Email address | `` |
| `SERVICE_EMAIL_PASSWORD` | Email password | `` |
| `SERVICE_EMAIL_SERVER` | SMTP server | `` |
| `SERVICE_EMAIL_PORT` | SMTP port | `` |

### Other Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `APPLICATION_ROOT` | Application root path | `/` |
| `EXTERNAL_APP` | External app flag | `0` |
| `CF_ALARMS_ENDPOINT` | Enable alarms endpoints | `0` |

## Application Access

### Without Ingress

```bash
# Port-forward for Cornflow
kubectl port-forward svc/my-cornflow-cornflow 5000:5000
```

### With Ingress

If you have enabled Ingress, you can access directly through the configured URLs.



## Monitoring

### Health Checks

- **Cornflow**: `/healthcheck`

### Logs

```bash
# Cornflow logs
kubectl logs -f deployment/my-cornflow-cornflow

# Cornflow PostgreSQL logs
kubectl logs -f deployment/my-project-cornflow-postgresql

# Airflow PostgreSQL logs (if Airflow is enabled)
kubectl logs -f deployment/my-cornflow-airflow-postgresql
```

## Scaling

### Horizontal Scaling

```bash
# Scale Cornflow
kubectl scale deployment my-cornflow-cornflow --replicas=3
```

### Autoscaling

Enable HPA (Horizontal Pod Autoscaler):

```yaml
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80
```

## Backup and Restoration

### Database Backup

```bash
# Cornflow backup
kubectl exec deployment/my-project-cornflow-postgresql -- pg_dump -U cornflow cornflow > cornflow_backup.sql

# Airflow backup (if Airflow is enabled)
kubectl exec deployment/my-cornflow-airflow-postgresql -- pg_dump -U airflow airflow > airflow_backup.sql
```

### Restoration

```bash
# Restore Cornflow
kubectl exec -i deployment/my-project-cornflow-postgresql -- psql -U cornflow cornflow < cornflow_backup.sql

# Restore Airflow (if Airflow is enabled)
kubectl exec -i deployment/my-cornflow-airflow-postgresql -- psql -U airflow airflow < airflow_backup.sql
```

## Troubleshooting

### Common Issues

1. **Pods not starting**
   - Verify that images are available
   - Check pod logs
   - Verify resource configuration

2. **Database connectivity issues**
   - Verify that PostgreSQL services are running
   - Check database credentials
   - Verify network configuration
   - Ensure each service connects to its correct database:
     - Cornflow → `my-project-cornflow-postgresql`
           - Airflow → `my-project-postgresql`

3. **Ingress issues**
   - Verify that Ingress controller is installed
   - Check Ingress annotations
   - Verify DNS configuration

### Useful Commands

```bash
# Check status of all resources
kubectl get all -l app.kubernetes.io/instance=my-cornflow

# Describe a pod for more details
kubectl describe pod <pod-name>

# Execute a shell in a pod
kubectl exec -it <pod-name> -- /bin/bash

# View namespace events
kubectl get events --sort-by='.lastTimestamp'
```

## Testing

The chart includes a comprehensive test suite located in the `tests/` directory.

### Quick Test (Validation Only)

For a quick validation without a Kubernetes cluster:

```bash
cd tests && ./quick-test.sh
```

This command:
- Validates chart syntax
- Generates templates with and without Airflow
- Shows the number of generated resources

### Complete Test (With Cluster)

If you have a Kubernetes cluster available (minikube, kind, etc.):

```bash
cd tests && ./test.sh
```

This command additionally:
- Installs the chart in a test namespace
- Verifies that pods are running
- Uninstalls the chart automatically

### Manual Testing

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

### Test Configuration

The `tests/` directory contains:

- **`test-values.yaml`**: Minimal values for testing without Airflow
- **`test-values-with-airflow.yaml`**: Values for testing with Airflow included
- **`test.sh`**: Complete automated test script
- **`quick-test.sh`**: Quick validation script
- **`TEST_README.md`**: Detailed testing documentation

For detailed testing information, see `tests/TEST_README.md`.

## Uninstallation

```bash
# Uninstall the release
helm uninstall my-cornflow

# Delete PVCs (optional)
kubectl delete pvc -l app.kubernetes.io/instance=my-cornflow
```

## Release Process

The chart is automatically released to Google Cloud Storage when a tag is pushed.

### Automatic Release (Recommended)

1. **Create and push a tag:**
   ```bash
   git tag helm-chart-v1.2.5
   git push origin helm-chart-v1.2.5
   ```

2. **The GitHub Action will automatically:**
   - Validate the chart
   - Package it
   - Upload to `gs://cornflow-public-artifacts/`
   - Create a GitHub release
   - Update the Helm repository index

### Manual Release

Use the release script for manual releases:

```bash
# Package chart locally
./scripts/release.sh -v 1.2.5 -p

# Upload to Google Cloud Storage (requires gcloud auth)
./scripts/release.sh -v 1.2.5 -u

# Complete release process
./scripts/release.sh -v 1.2.5 -a
```

### Repository Information

- **Repository URL**: `https://storage.googleapis.com/cornflow-public-artifacts/`
- **Bucket**: `gs://cornflow-public-artifacts/`
- **Installation**: `helm repo add cornflow https://storage.googleapis.com/cornflow-public-artifacts/`

## Contributing

To contribute to this chart:

1. Fork the repository
2. Create a branch for your feature
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This chart is under the same license as Cornflow.

## Support

For support and questions:

- [GitHub Issues](https://github.com/baobabsoluciones/cornflow/issues)
- [Cornflow Documentation](https://cornflow.readthedocs.io/)
- Email: cornflow@baobabsoluciones.es 