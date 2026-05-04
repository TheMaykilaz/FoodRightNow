# Kubernetes vs Docker Compose — Analysis

## 1. How Deployment Works

### Kubernetes Deployment Object
A **Deployment** in Kubernetes is a declarative resource that manages the lifecycle of Pods:

```
User writes YAML → kubectl apply → API Server → Controller Manager → Scheduler → Kubelet → Container Runtime → Pod
```

Key mechanisms:
- **Desired State**: You declare `replicas: 2`, and the Deployment Controller ensures exactly 2 pods exist at all times.
- **ReplicaSet**: Deployment creates a ReplicaSet under the hood, which is responsible for maintaining the correct number of pod replicas.
- **Rolling Updates**: When you change the image/config, Deployment creates a *new* ReplicaSet and gradually shifts traffic (controlled by `maxSurge` and `maxUnavailable`).
- **Health Checks**: `readinessProbe` prevents traffic to unready pods; `livenessProbe` restarts unresponsive pods automatically.
- **Self-Healing**: If a pod crashes or is deleted, the ReplicaSet controller creates a replacement immediately.

### Our Deployment Example (order-service)
```yaml
spec:
  replicas: 2                    # Always maintain 2 pods
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                # Allow 1 extra pod during update
      maxUnavailable: 0          # Never reduce below desired count
```

---

## 2. Differences: Docker Compose vs Kubernetes

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Scope** | Single machine | Multi-node cluster |
| **Scaling** | Manual (`docker-compose up --scale`) | Declarative (`replicas: N`), auto-scaling via HPA |
| **Self-Healing** | None — if container dies, it stays dead (unless `restart: always`) | Automatic — Deployment controller recreates pods |
| **Load Balancing** | Basic (round-robin via Docker DNS) | Built-in Service with kube-proxy (iptables/IPVS) |
| **Rolling Updates** | Not supported (stop → rebuild → start) | Native with zero-downtime (`RollingUpdate` strategy) |
| **Rollback** | Manual | One command: `kubectl rollout undo` |
| **Service Discovery** | Container name DNS | ClusterIP Service + DNS (`service-name.namespace.svc.cluster.local`) |
| **Resource Limits** | Optional `mem_limit`, `cpus` | Enforced `requests` and `limits` with QoS classes |
| **Health Checks** | Basic `healthcheck` (no action on failure) | Liveness (restart), Readiness (remove from traffic) |
| **Storage** | Docker volumes (local) | PersistentVolumes (local, cloud, NFS, etc.) |
| **Networking** | Single bridge network | Pod network (CNI), Service network, Ingress |
| **Config Management** | `.env` files, `environment:` | ConfigMaps, Secrets (with encryption) |
| **Production Ready** | Development/testing only | Production-grade orchestration |

### Concrete Example from Our Project

**Docker Compose** (`docker-compose.yml`):
```yaml
order_service:
  build: ./order_service
  ports:
    - "8001:8001"
  environment:
    - REDIS_URL=redis://redis:6379
  depends_on:
    redis:
      condition: service_healthy
```
- Single container, no redundancy
- If it crashes, manual restart needed
- No traffic management

**Kubernetes** (`order-service-deployment.yaml`):
```yaml
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
  template:
    spec:
      containers:
        - readinessProbe: ...
          livenessProbe: ...
          resources:
            requests: { memory: "128Mi", cpu: "100m" }
            limits: { memory: "256Mi", cpu: "250m" }
```
- 2 replicas with load balancing
- Auto-restart on crash
- Zero-downtime updates
- Resource guarantees

---

## 3. Advantages of Orchestration (Kubernetes)

### 3.1 High Availability
- Multiple replicas ensure service stays available even if pods fail
- Self-healing replaces failed pods automatically
- **Demo proof**: We deleted a pod and the service remained accessible

### 3.2 Scalability
- Scale from 2 to 4 replicas with one command
- Horizontal Pod Autoscaler (HPA) can auto-scale based on CPU/memory
- **Demo proof**: `kubectl scale deployment order-service --replicas=4`

### 3.3 Zero-Downtime Deployments
- Rolling updates gradually replace old pods with new ones
- Rollback to previous version if something goes wrong
- **Demo proof**: Updated version label v1 → v2 with no downtime

### 3.4 Resource Management
- CPU and memory limits prevent one service from starving others
- Quality of Service (QoS) classes prioritize critical pods

### 3.5 Service Discovery & Load Balancing
- Built-in DNS: `order-service.delivery-system.svc.cluster.local`
- kube-proxy distributes traffic across all healthy pods
- **Demo proof**: 10 requests were distributed across 4 order-service pods

### 3.6 Declarative Configuration
- Infrastructure as Code — entire system described in YAML
- Version controlled, reproducible, auditable
- `kubectl apply` brings cluster to desired state

### 3.7 Multi-Environment Support
- Same manifests work on local (Minikube), cloud (GKE, EKS, AKS)
- ConfigMaps/Secrets separate config from code

---

## 4. Demonstration Scenario Summary

| Step | What We Tested | Command |
|------|---------------|---------|
| 1 | Service availability | `GET /health` on all 4 services |
| 2 | Inter-service communication | Order → Courier assignment + Tracking |
| 3 | Redis caching | X-Cache: MISS → HIT + Redis KEYS |
| 4 | Horizontal scaling | `kubectl scale --replicas=4` |
| 5 | Load balancing | 10 requests across 4 pods + endpoints check |
| 6 | Self-healing | `kubectl delete pod` → new pod auto-created |
| 7 | Rolling update | Version v1 → v2 with zero downtime |
| 8 | Scale down | `kubectl scale --replicas=2` |

### Architecture Diagram
```
                    ┌──────────────────────────────────────────────┐
                    │           Minikube Cluster                   │
                    │                                              │
  Browser ──────►   │  ┌─────────────┐    ┌──────────────────┐    │
  localhost:8000    │  │  Frontend    │    │  Redis           │    │
                    │  │  (1 pod)     │    │  (1 pod)         │    │
                    │  └─────────────┘    │  ClusterIP:6379  │    │
                    │                      └──────────────────┘    │
  Postman ──────►   │  ┌──────────────────┐                       │
  localhost:8001    │  │  Order Service    │──► Courier Service    │
                    │  │  (2 pods, LB)     │   (1 pod, :8002)     │
                    │  └──────────────────┘                       │
                    │  ┌──────────────────┐  ┌─────────────────┐  │
  localhost:8003    │  │ Tracking Service  │  │Reporting Service│  │
                    │  │  (1 pod)          │  │  (1 pod)        │  │
                    │  └──────────────────┘  └─────────────────┘  │
                    │                                              │
                    │  ┌──────────────────────────────────────┐   │
                    │  │  PersistentVolume: SQLite (shared)    │   │
                    │  └──────────────────────────────────────┘   │
                    └──────────────────────────────────────────────┘
```
