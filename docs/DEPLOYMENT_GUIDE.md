# Production Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Infrastructure Requirements](#infrastructure-requirements)
- [Container Orchestration](#container-orchestration)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Scaling Strategies](#scaling-strategies)

## Overview

This guide provides comprehensive instructions for deploying the Audio Quality Assessment Toolkit in production environments, following Google SRE and Meta infrastructure best practices.

## Infrastructure Requirements

### Minimum System Requirements

| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| **Single Instance** | 2 cores | 4GB RAM | 10GB SSD | 1Gbps |
| **Production Cluster** | 8+ cores | 16GB+ RAM | 100GB+ SSD | 10Gbps |
| **High Availability** | 16+ cores | 32GB+ RAM | 500GB+ SSD | 10Gbps |

### Recommended Cloud Configurations

#### Google Cloud Platform
```bash
# GKE Cluster
gcloud container clusters create audio-quality-cluster \\
  --zone us-central1-a \\
  --machine-type e2-standard-4 \\
  --num-nodes 3 \\
  --enable-autoscaling \\
  --min-nodes 1 \\
  --max-nodes 10 \\
  --enable-autorepair \\
  --enable-autoupgrade
```

#### AWS ECS
```json
{
  "family": "audio-quality-toolkit",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole"
}
```

#### Azure Container Instances
```yaml
apiVersion: 2021-03-01
location: eastus
properties:
  containers:
  - name: audio-quality-toolkit
    properties:
      image: audio-quality-toolkit:latest
      resources:
        requests:
          cpu: 2
          memoryInGb: 8
```

## Container Orchestration

### Kubernetes Manifests

#### Production Deployment
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audio-quality-toolkit
  labels:
    app: audio-quality-toolkit
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: audio-quality-toolkit
  template:
    metadata:
      labels:
        app: audio-quality-toolkit
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: audio-processor
        image: audio-quality-toolkit:1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
            ephemeral-storage: 5Gi
          limits:
            cpu: 2000m
            memory: 8Gi
            ephemeral-storage: 20Gi
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_FORMAT
          value: "json"
        - name: METRICS_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: temp-storage
          mountPath: /tmp
        - name: model-cache
          mountPath: /app/cache
      volumes:
      - name: temp-storage
        emptyDir:
          sizeLimit: 10Gi
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
```

#### Service Configuration
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: audio-quality-service
  labels:
    app: audio-quality-toolkit
spec:
  type: ClusterIP
  selector:
    app: audio-quality-toolkit
  ports:
  - port: 80
    targetPort: 8080
    name: http
```

#### Ingress Configuration
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: audio-quality-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - audio-api.example.com
    secretName: audio-api-tls
  rules:
  - host: audio-api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: audio-quality-service
            port:
              number: 80
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: audio-quality-toolkit

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e ".[dev]"

    - name: Lint with flake8
      run: |
        flake8 src/ tests/

    - name: Type check with mypy
      run: |
        mypy src/

    - name: Test with pytest
      run: |
        pytest tests/ --cov=src/ --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./Dockerfile.production
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
    - uses: actions/checkout@v4

    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}

    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f k8s/
        kubectl rollout status deployment/audio-quality-toolkit
        kubectl get services -o wide
```

### GitLab CI/CD Pipeline
```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_REGISTRY: registry.gitlab.com
  DOCKER_IMAGE: $DOCKER_REGISTRY/$CI_PROJECT_PATH
  KUBERNETES_NAMESPACE: audio-quality

test:
  stage: test
  image: python:3.10
  before_script:
    - pip install -r requirements.txt
    - pip install -e ".[dev]"
  script:
    - pytest tests/ --cov=src/ --cov-report=xml --cov-report=term
    - flake8 src/ tests/
    - mypy src/
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  coverage: '/TOTAL.+ ([0-9]{1,3}%)/'

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -f Dockerfile.production -t $DOCKER_IMAGE:$CI_COMMIT_SHA .
    - docker push $DOCKER_IMAGE:$CI_COMMIT_SHA
    - docker tag $DOCKER_IMAGE:$CI_COMMIT_SHA $DOCKER_IMAGE:latest
    - docker push $DOCKER_IMAGE:latest

deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  before_script:
    - kubectl config use-context $KUBE_CONTEXT
  script:
    - sed -i "s|IMAGE_TAG|$CI_COMMIT_SHA|g" k8s/deployment.yaml
    - kubectl apply -f k8s/ -n $KUBERNETES_NAMESPACE
    - kubectl rollout status deployment/audio-quality-toolkit -n $KUBERNETES_NAMESPACE
  only:
    - main
```

## Monitoring & Observability

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
- job_name: 'audio-quality-toolkit'
  static_configs:
  - targets: ['audio-quality-service:80']
  scrape_interval: 30s
  metrics_path: /metrics
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Audio Quality Toolkit",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

### Logging Stack (ELK)
```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/log/containers/*.log'
  processors:
  - add_kubernetes_metadata:
      in_cluster: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "audio-quality-toolkit-%{+yyyy.MM.dd}"

# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [kubernetes][container][name] == "audio-processor" {
    json {
      source => "message"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "audio-quality-toolkit-%{+yyyy.MM.dd}"
  }
}
```

## Security

### Pod Security Standards
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: audio-quality-toolkit
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: audio-processor
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
        - ALL
```

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: audio-quality-network-policy
spec:
  podSelector:
    matchLabels:
      app: audio-quality-toolkit
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

## Scaling Strategies

### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: audio-quality-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: audio-quality-toolkit
  minReplicas: 3
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaler
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: audio-quality-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: audio-quality-toolkit
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: audio-processor
      maxAllowed:
        cpu: 4000m
        memory: 16Gi
      minAllowed:
        cpu: 100m
        memory: 512Mi
```

### Performance Optimization

#### Resource Limits and Requests
```yaml
resources:
  requests:
    cpu: 500m
    memory: 2Gi
    ephemeral-storage: 5Gi
  limits:
    cpu: 2000m
    memory: 8Gi
    ephemeral-storage: 20Gi
```

#### JVM Tuning (if applicable)
```bash
export JAVA_OPTS="-Xms2g -Xmx6g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
```

#### Model Caching Strategy
```yaml
volumeMounts:
- name: model-cache
  mountPath: /app/cache
volumes:
- name: model-cache
  persistentVolumeClaim:
    claimName: model-cache-pvc
```

This comprehensive deployment guide ensures production-ready deployment following industry best practices for containerized AI/ML applications.