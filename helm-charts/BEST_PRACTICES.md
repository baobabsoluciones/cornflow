# Best Practices for Cornflow Helm Chart

This document contains the recommended best practices for deploying and managing Cornflow in Kubernetes using this Helm chart.

## 🔐 Security

### Secret Management

**❌ DON'T do:**
```yaml
# Never include passwords in values.yaml
cornflow:
  env:
    SECRET_KEY: "my-secret-key"
    CORNFLOW_ADMIN_PWD: "admin123"
```

**✅ DO:**
```yaml
# Use Kubernetes Secrets
cornflow:
  env:
    SECRET_KEY: ${SECRET_KEY}
    CORNFLOW_ADMIN_PWD: ${ADMIN_PASSWORD}
```

Create a Secret:
```bash
kubectl create secret generic cornflow-secrets \
  --from-literal=SECRET_KEY="your-super-secret-key" \
  --from-literal=ADMIN_PASSWORD="your-secure-password" \
  --from-literal=DB_PASSWORD="your-db-password"
```

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

## 🌐 Ingress and TLS

### Ingress Configuration

**Production with TLS:**
```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
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

### Rate Limiting

Configure rate limiting:
```yaml
ingress:
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
```

## 🔧 Application Configuration

### Critical Environment Variables

**Security Variables:**
```yaml
cornflow:
  env:
    # Authentication
    AUTH_TYPE: "2"  # Use OID for production
    SECRET_KEY: "your-super-secure-secret"
    SECRET_BI_KEY: "your-super-secure-bi-secret"
    
    # User Management
    SIGNUP_ACTIVATED: "0"  # Disable in production
    SERVICE_USER_ALLOW_PASSWORD_LOGIN: "0"  # Disable in production
    OPEN_DEPLOYMENT: "0"  # Disable in production
    
    # Access Control
    CORS_ORIGINS: "https://your-domain.com"
    USER_ACCESS_ALL_OBJECTS: "0"
    
    # Token Management
    TOKEN_DURATION: "24"  # Hours
    PWD_ROTATION_TIME: "90"  # Days
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
    # Security
    SECRET_KEY: ${SECRET_KEY}
    SECRET_BI_KEY: ${SECRET_BI_KEY}
    
    # Database
    DATABASE_URL: "postgresql://cornflow:${DB_PASSWORD}@cornflow-postgresql:5432/cornflow"
    
    # Application configuration
    AUTH_TYPE: "1"  # Database authentication
    SIGNUP_ACTIVATED: "0"  # Disable in production
    SERVICE_USER_ALLOW_PASSWORD_LOGIN: "0"  # More secure
    OPEN_DEPLOYMENT: "0"  # More restrictive
    
    # Token configuration
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

3. **Ingress issues**
   - Verify Ingress controller is installed
   - Check Ingress annotations
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

## 📋 Production Checklist

- [ ] Secrets configured correctly
- [ ] RBAC enabled
- [ ] Network Policies configured
- [ ] Ingress with TLS enabled
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
- [Cornflow Documentation](https://cornflow.readthedocs.io/) 