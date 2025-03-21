# DevOps Automation Platform Helm Chart

This Helm chart deploys the DevOps Automation Platform with all its components including:
- Main application
- CI, Helm, and Deploy agents
- Prometheus monitoring
- Grafana dashboards
- PostgreSQL database

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Ingress controller (e.g., nginx-ingress)
- PV provisioner support in the underlying infrastructure

## Installation

1. Add required Helm repositories:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

2. Install the chart:
```bash
helm install devops-automation ./helm
```

3. To install with custom values:
```bash
helm install devops-automation ./helm -f custom-values.yaml
```

## Configuration

The following table lists the configurable parameters and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `production` |
| `global.domain` | Domain name for ingress | `devops-automation.local` |
| `mainApp.replicas` | Number of main app replicas | `2` |
| `mainApp.image.tag` | Image tag | `latest` |
| `postgresql.postgresqlUsername` | PostgreSQL username | `devops` |
| `postgresql.postgresqlPassword` | PostgreSQL password | `devops123` |
| `grafana.adminPassword` | Grafana admin password | `admin` |

For complete list of parameters, see `values.yaml`.

## Component Details

### Main Application
- Deployed with multiple replicas for high availability
- Includes health checks and resource limits
- Automatically connects to PostgreSQL database
- Exposes metrics for Prometheus

### Agent Services
- CI Agent: Handles CI pipeline creation and management
- Helm Agent: Manages Helm chart operations
- Deploy Agent: Handles deployment operations
- Each agent runs independently with its own service

### Monitoring Stack
- Prometheus: Collects metrics from all services
- Grafana: Provides visualization with pre-configured dashboards
- Custom dashboards for:
  - System metrics
  - Task processing statistics
  - Service health status

### Database
- PostgreSQL database with persistent storage
- Automatic migrations handled by init containers
- Configurable backup and retention policies

## Accessing the Application

1. Update your DNS or hosts file to point the domain to your cluster's ingress IP
2. Access the application at: `http://devops-automation.local`
3. Grafana dashboard: `http://devops-automation.local/grafana`
4. Prometheus: `http://devops-automation.local/prometheus`

### Default Credentials
- Grafana:
  - Username: `admin`
  - Password: `admin` (change in production)
- Database:
  - Username: `devops`
  - Password: `devops123` (change in production)

## Production Configuration

For production deployments, you should:
1. Set proper passwords for Grafana and PostgreSQL
2. Enable SSL/TLS using cert-manager or your preferred certificate solution
3. Configure proper resource limits based on your workload
4. Set up proper backup solutions for PostgreSQL and persistent volumes
5. Configure alerting in Prometheus/Grafana

## Troubleshooting

1. Check pod status:
```bash
kubectl get pods -l app=devops-service
```

2. View application logs:
```bash
kubectl logs -l app=devops-service
```

3. Common issues:
- Database connection failures: Check PostgreSQL pod status and credentials
- Agent connectivity: Verify service discovery and network policies
- Persistence issues: Check PVC status and storage class

## Uninstallation

```bash
helm uninstall devops-automation
```

Note: This will not delete persistent volumes. To clean up PVs:
```bash
kubectl delete pvc -l release=devops-automation