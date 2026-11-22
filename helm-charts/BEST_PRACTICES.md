# Best Practices for Cornflow Helm Chart

This document contains the recommended best practices for deploying and managing Cornflow in Kubernetes using this Helm chart.

## 🔐 Security

### Secret Management

**❌ DON'T do:**
```yaml
# Never include keys or passwords in values.yaml
cornflow:
  env:
    FERNET_KEY: "my-secret-key"  # rejected by the chart: keys go in a Secret
    CORNFLOW_ADMIN_PWD: "admin123"
```

**✅ DO:**
```yaml
# Use Kubernetes Secrets
cornflow:
  env:
    CORNFLOW_ADMIN_PWD: ${ADMIN_PASSWORD}
```

Create a Secret:
```bash
kubectl create secret generic cornflow-secrets \
  --from-literal=ADMIN_PASSWORD="your-secure-password" \
  --from-literal=DB_PASSWORD="your-db-password"
```

### Secret keys (`FERNET_KEY` and `SECRET_BI_KEY`)

- By default the chart creates the Secret `<release>-cornflow-keys` with random keys on install, reuses them on every upgrade and keeps the Secret on `helm uninstall`. Back it up together with the database: a new `FERNET_KEY` invalidates every session and API key and locks out the users with MFA until an administrator resets it, and a new `SECRET_BI_KEY` invalidates the BI tokens.
- With `helm template` or GitOps tools that render without the cluster (for example Argo CD), or when you manage the keys yourself, create the Secret and set `cornflow.keys.existingSecret`. Otherwise the keys change on every render.

```bash
kubectl create secret generic cornflow-keys \
  --from-literal=FERNET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  --from-literal=SECRET_BI_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

```yaml
cornflow:
  keys:
    existingSecret: cornflow-keys
```

- Never set `FERNET_KEY`, `SECRET_KEY` or `SECRET_BI_KEY` in `cornflow.env`: the chart fails to render. `SECRET_KEY` is only a fallback of `FERNET_KEY` in cornflow and is not needed with this chart.

Details, including how to upgrade from a previous version of the chart: [Secret keys](cornflow/README.md#secret-keys).

### Security level

Set `CORNFLOW_SECURITY_LEVEL` in `cornflow.env` (1 by default):

- `1`: same behaviour as cornflow 1.3.9.
- `2`: password policy, single-use password on user creation, account lockout after 5 failed logins, 8-hour sessions and a mandatory secret key of 32 bytes or more.
- `3`: level 2 plus mandatory MFA, sessions with token refresh, password rotation, BI tokens that expire, and production CORS, Swagger and HSTS settings.

`SIGNUP_ACTIVATED`, `CORS_ORIGINS`, `TOKEN_DURATION` and `PWD_ROTATION_TIME` are set in the chart's `values.yaml` and override the level: at levels 2 and 3 set them to `null` (or to the value you want). See [Security level](cornflow/README.md#security-level) and the cornflow documentation in [`docs/source/deploy/access.rst`](../docs/source/deploy/access.rst).

### RBAC Configuration

Always enable ServiceAccount creation:
```yaml
serviceAccount:
  create: true
  name: ""
  annotations: {}
```

### Network Configuration

**For production:**
```yaml
# Use Network Policies
networkPolicy:
  enabled: true
  ingressRules:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 5000
```

## 📊 Monitoring and Observability

### Health Checks

Health checks are configured by default:
- **Cornflow**: `/health`

### Logging

Configure structured logging:
```yaml
cornflow:
  env:
    LOG_LEVEL: "INFO"
    LOG_FORMAT: "json"
```

### Metrics

Enable ServiceMonitor for Prometheus:
```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    scrapeTimeout: 10s
```

## 🔄 Scalability

### Horizontal Pod Autoscaler

For variable loads:
```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 70
```

### Pod Disruption Budget

For high availability:
```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

### Resources

**Development:**
```yaml
cornflow:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi
```

**Production:**
```yaml
cornflow:
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi
```

## 💾 Persistence

### Storage Classes

Use appropriate Storage Classes:
```yaml
persistence:
  enabled: true
  storageClass: "fast-ssd"  # For production
  size: 20Gi
  accessMode: ReadWriteOnce
```

### Backup Strategy

Implement regular backups:
```bash
# Automatic PostgreSQL backup
kubectl exec deployment/my-cornflow-postgresql -- \
  pg_dump -U cornflow cornflow | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

## 🌐 External Access and TLS

### Ingress Configuration

**Note:** The chart does not include Ingress resources by default. Use separate Ingress files for external access.

**Production with TLS:**
```yaml
# Create a separate ingress.yaml file
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cornflow-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  ingressClassName: nginx
  tls:
    - secretName: cornflow-tls
      hosts:
        - cornflow.mydomain.com
  rules:
    - host: cornflow.mydomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-cornflow-cornflow-server
                port:
                  number: 5000
```

**Apply the Ingress:**
```bash
kubectl apply -f ingress.yaml
```

### Best Practices for External Ingress

1. **Use separate Ingress files** for different environments:
   ```bash
   # Development
   kubectl apply -f ingress-dev.yaml
   
   # Staging
   kubectl apply -f ingress-staging.yaml
   
   # Production
   kubectl apply -f ingress-prod.yaml
   ```

2. **Version control your Ingress configurations** alongside your application code

3. **Use Helm hooks** if you need to manage Ingress with Helm:
   ```yaml
   # In a separate chart or using Helm hooks
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: cornflow-ingress
     annotations:
       helm.sh/hook: post-install,post-upgrade
       helm.sh/hook-weight: "1"
   ```

4. **Separate concerns** - keep Ingress configuration separate from application configuration

## 🔧 Application Configuration

### Critical Environment Variables

**Security Variables:**
```yaml
cornflow:
  keys:
    existingSecret: "cornflow-keys"  # or leave it empty and let the chart generate the keys
  env:
    # Security level (1, 2 or 3): sets the defaults of the security settings
    CORNFLOW_SECURITY_LEVEL: "3"

    # Authentication
    AUTH_TYPE: "2"  # Use OID for production

    # User Management
    SIGNUP_ACTIVATED: null  # let the security level decide (a value here overrides it)
    SERVICE_USER_ALLOW_PASSWORD_LOGIN: "0"  # Disable in production
    OPEN_DEPLOYMENT: "0"  # Disable in production

    # Access Control
    CORS_ORIGINS: "https://your-domain.com"  # overrides the level (closed at level 3)
    USER_ACCESS_ALL_OBJECTS: "0"

    # Token Management: let the security level decide
    TOKEN_DURATION: null
    PWD_ROTATION_TIME: null
```

**Authentication Configuration:**

**LDAP Authentication:**
```yaml
cornflow:
  env:
    AUTH_TYPE: "1"  # Database auth (LDAP uses DB backend)
    LDAP_HOST: "ldap://your-ldap-server:389"
    LDAP_BIND_DN: "cn=admin,dc=yourcompany,dc=com"
    LDAP_BIND_PASSWORD: "your-ldap-password"
    LDAP_USER_BASE: "ou=users,dc=yourcompany,dc=com"
    LDAP_GROUP_BASE: "dc=yourcompany,dc=com"
    LDAP_GROUP_TO_ROLE_ADMIN: "cornflow-admins"
    LDAP_GROUP_TO_ROLE_PLANNER: "cornflow-planners"
    LDAP_GROUP_TO_ROLE_VIEWER: "cornflow-viewers"
```

**OpenID Connect Authentication:**
```yaml
cornflow:
  env:
    AUTH_TYPE: "2"  # OID authentication
    OID_PROVIDER: "https://your-oid-provider.com"
    OID_EXPECTED_AUDIENCE: "your-audience-id"
```

**Email Configuration:**
```yaml
cornflow:
  env:
    SERVICE_EMAIL_ADDRESS: "noreply@yourcompany.com"
    SERVICE_EMAIL_PASSWORD: "your-email-password"
    SERVICE_EMAIL_SERVER: "smtp.yourcompany.com"
    SERVICE_EMAIL_PORT: "587"
```

```yaml
cornflow:
  env:
    # Security: FERNET_KEY and SECRET_BI_KEY come from the keys Secret (cornflow.keys)
    
    # Database
    DATABASE_URL: "postgresql://cornflow:${DB_PASSWORD}@cornflow-postgresql:5432/cornflow"
    
    # Application configuration
    AUTH_TYPE: "1"  # Database authentication
    SIGNUP_ACTIVATED: "0"  # Disable in production (overrides the security level)
    SERVICE_USER_ALLOW_PASSWORD_LOGIN: "0"  # More secure
    OPEN_DEPLOYMENT: "0"  # More restrictive
    
    # Token configuration (overrides the security level; null lets the level decide)
    TOKEN_DURATION: "24"
    PWD_ROTATION_TIME: "90"
```

### CORS Configuration

```yaml
cornflow:
  env:
    CORS_ORIGINS: "https://cornflow.mydomain.com,https://app.mydomain.com"
```

## 🚀 Deployment

### Deployment Strategy

**Rolling Update (recommended):**
```yaml
cornflow:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Image Configuration

**Production:**
```yaml
image:
  repository: baobabsoluciones/cornflow
  tag: "release-v1.2.3"
  pullPolicy: Always  # Always verify image
```

### Namespace Strategy

Use separate namespaces:
```bash
# Create dedicated namespace
kubectl create namespace cornflow-prod

# Install in specific namespace
helm install cornflow-prod ./cornflow --namespace cornflow-prod
```

## 🔍 Troubleshooting

### Useful Commands

```bash
# Check deployment status
kubectl get all -l app.kubernetes.io/instance=my-cornflow

# View logs in real-time
kubectl logs -f deployment/my-cornflow-cornflow

# Describe pod for debugging
kubectl describe pod <pod-name>

# Execute shell in pod
kubectl exec -it <pod-name> -- /bin/bash

# Check database connectivity
kubectl exec deployment/my-cornflow-postgresql -- pg_isready -U cornflow
```

### Common Issues

1. **Pods in Pending state**
   - Check available resources
   - Review StorageClass
   - Verify nodeSelector/affinity

2. **Database connectivity errors**
   - Verify credentials
   - Check network configuration
   - Verify PostgreSQL is ready

3. **External access issues**
   - Verify Ingress controller is installed
   - Check Ingress configuration in separate files
   - Verify DNS configuration

## 📈 Optimization

### Database Configuration

```yaml
postgresql:
  primary:
    persistence:
      size: 20Gi
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
      requests:
        cpu: 500m
        memory: 512Mi
```



## 🔄 CI/CD

### Deployment Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Cornflow
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Kubernetes
        run: |
          helm upgrade --install cornflow-prod ./helm-charts/cornflow \
            --namespace cornflow-prod \
            --values values-cornflow.yaml \
            --set image.tag=${{ github.sha }}
```

### Secret Management in CI/CD

Use tools like:
- Sealed Secrets
- External Secrets Operator
- HashiCorp Vault

Point `cornflow.keys.existingSecret` to the Secret these tools create.

## 📋 Production Checklist

- [ ] Secrets configured correctly
- [ ] Keys Secret backed up with the database, or `cornflow.keys.existingSecret` set (required with tools that render with `helm template`)
- [ ] `CORNFLOW_SECURITY_LEVEL` set, and `SIGNUP_ACTIVATED`, `CORS_ORIGINS`, `TOKEN_DURATION` and `PWD_ROTATION_TIME` reviewed (they override the level)
- [ ] RBAC enabled
- [ ] Network Policies configured
- [ ] External Ingress with TLS configured
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] HPA configured
- [ ] PDB enabled
- [ ] Appropriate resources configured
- [ ] Structured logging enabled
- [ ] Health checks working
- [ ] Rate limiting configured
- [ ] CORS configured correctly
- [ ] Public registration disabled
- [ ] Password rotation enabled

## 📚 Additional Resources

- [Official Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/)
- [Cornflow Documentation](https://baobabsoluciones.github.io/cornflow/) 
