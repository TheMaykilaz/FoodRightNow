# Kubernetes Deployment Report — Delivery System Microservices

---

## 1. Problem Statement

### 1.1 Deployed Services

| Service | Port | Replicas | Purpose |
|---------|------|----------|---------|
| **order-service** | 8001 | 2 (scalable) | Order CRUD, user management, courier assignment, payments |
| **courier-service** | 8002 | 1 | Courier management, availability tracking |
| **tracking-service** | 8003 | 1 | Real-time delivery tracking |
| **reporting-service** | 8004 | 1 | Delivery reports, daily/weekly statistics |
| **frontend** | 8000 | 1 | Web UI serving static files |
| **redis** | 6379 | 1 | Caching layer (ClusterIP, internal only) |

### 1.2 Created Deployments

```
$ kubectl get deployments -n delivery-system

NAME                READY   UP-TO-DATE   AVAILABLE
order-service       2/2     2            2
courier-service     1/1     1            1
tracking-service    1/1     1            1
reporting-service   1/1     1            1
frontend            1/1     1            1
redis               1/1     1            1
```

Total: **6 Deployments**, **7 Pods** (order-service has 2 replicas).

### 1.3 Scaling Implementation

| Aspect | Configuration |
|--------|--------------|
| Initial replicas (order-service) | 2 |
| Scaled to | 4 replicas |
| Strategy | `RollingUpdate` |
| `maxSurge` | 1 (allow 1 extra pod during update) |
| `maxUnavailable` | 0 (never reduce below desired count) |
| Scale command | `kubectl scale deployment order-service --replicas=4` |

---

## 2. Design

### 2.1 Cluster Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MINIKUBE CLUSTER (Single Node)                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Namespace: delivery-system                 │   │
│  │                                                              │   │
│  │  ┌────────────────┐          ┌────────────────────────┐     │   │
│  │  │   ConfigMap     │          │   PersistentVolume      │     │   │
│  │  │  (env vars)     │          │   (SQLite DB, 100Mi)    │     │   │
│  │  └────────────────┘          └────────────────────────┘     │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  order-service (Deployment, 2 replicas)               │   │   │
│  │  │  ┌─────────┐  ┌─────────┐                            │   │   │
│  │  │  │  Pod 1   │  │  Pod 2   │  ← NodePort :30001       │   │   │
│  │  │  └─────────┘  └─────────┘                            │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │   │
│  │  │courier-service│ │tracking-svc  │ │reporting-svc │        │   │
│  │  │ (1 pod)       │ │ (1 pod)      │ │ (1 pod)      │        │   │
│  │  │ NP:30002      │ │ NP:30003     │ │ NP:30004     │        │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────────────────────────┐     │   │
│  │  │   frontend    │ │   redis (ClusterIP, internal)     │     │   │
│  │  │ (1 pod)       │ │   (1 pod, port 6379)             │     │   │
│  │  │ NP:30000      │ └──────────────────────────────────┘     │   │
│  │  └──────────────┘                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         ▲
         │ kubectl port-forward (localhost:8000-8004)
         │
    ┌────────────┐
    │   Client    │ (Browser / Postman)
    └────────────┘
```

### 2.2 Component Interactions

```
Client (Postman/Browser)
    │
    ├── GET/POST ──► order-service ──► Redis (cache check)
    │                     │
    │                     ├── HTTP ──► courier-service (assign courier)
    │                     │                  │
    │                     │                  └── SQLite DB (read/write)
    │                     │
    │                     └── SQLite DB (orders, users)
    │
    ├── GET ──► tracking-service ──► Redis ──► SQLite DB
    │
    ├── GET ──► reporting-service ──► Redis ──► SQLite DB
    │
    └── GET ──► frontend (static HTML/JS/CSS)
```

**Inter-service communication:**
- order-service → courier-service: HTTP REST call via K8s DNS (`http://courier-service:8002`)
- All services → Redis: TCP via K8s DNS (`redis://redis-service:6379`)
- All services → SQLite: Shared PersistentVolume mounted at `/data/delivery.db`

### 2.3 Structure of YAML Files

```
k8s/
├── namespace.yaml                    # Namespace: delivery-system
├── configmap.yaml                    # Shared environment variables
├── pv-database.yaml                  # PersistentVolume + PVC for SQLite
├── redis-deployment.yaml             # Redis Deployment (1 replica)
├── redis-service.yaml                # Redis ClusterIP Service
├── seed-job.yaml                     # One-time Job to seed database
├── order-service-deployment.yaml     # Order Deployment (2 replicas)
├── order-service-svc.yaml            # Order NodePort Service
├── courier-service-deployment.yaml   # Courier Deployment (1 replica)
├── courier-service-svc.yaml          # Courier NodePort Service
├── tracking-service-deployment.yaml  # Tracking Deployment (1 replica)
├── tracking-service-svc.yaml         # Tracking NodePort Service
├── reporting-service-deployment.yaml # Reporting Deployment (1 replica)
├── reporting-service-svc.yaml        # Reporting NodePort Service
├── frontend-deployment.yaml          # Frontend Deployment (1 replica)
├── frontend-svc.yaml                 # Frontend NodePort Service
├── deploy.ps1                        # Automated deployment script
├── demo.ps1                          # Demo scenario script
├── ANALYSIS.md                       # Detailed analysis document
└── REPORT.md                         # This report
```

---

## 3. Implementation

### 3.1 Deployment YAML (example: order-service)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: delivery-system
spec:
  replicas: 2                          # High availability
  selector:
    matchLabels:
      app: order-service
  strategy:
    type: RollingUpdate                # Zero-downtime updates
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: order-service
        version: v1
    spec:
      containers:
        - name: order-service
          image: order-service:latest
          imagePullPolicy: Never       # Use local Minikube images
          ports:
            - containerPort: 8001
          envFrom:
            - configMapRef:
                name: delivery-config  # Inject all env vars from ConfigMap
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "250m"
          readinessProbe:              # Only receive traffic when ready
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:               # Restart if unresponsive
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 15
            periodSeconds: 10
          volumeMounts:
            - name: db-storage
              mountPath: /data
      volumes:
        - name: db-storage
          persistentVolumeClaim:
            claimName: delivery-db-pvc
```

### 3.2 Service YAML (example: order-service)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: delivery-system
spec:
  type: NodePort                      # Accessible externally via NodePort
  selector:
    app: order-service                # Routes to all pods with this label
  ports:
    - port: 8001                      # Internal cluster port
      targetPort: 8001                # Container port
      nodePort: 30001                 # External access port
```

**Service types used:**
- `NodePort` — order, courier, tracking, reporting, frontend (external access)
- `ClusterIP` — redis (internal only, no external access needed)

### 3.3 kubectl Commands

```powershell
# --- Deployment ---
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pv-database.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f redis-service.yaml
kubectl apply -f seed-job.yaml
kubectl apply -f order-service-deployment.yaml
kubectl apply -f order-service-svc.yaml

# --- Monitoring ---
kubectl get pods -n delivery-system -o wide
kubectl get services -n delivery-system
kubectl get deployments -n delivery-system
kubectl logs deployment/order-service -n delivery-system
kubectl describe pod <pod-name> -n delivery-system

# --- Scaling ---
kubectl scale deployment order-service -n delivery-system --replicas=4
kubectl get pods -n delivery-system -l app=order-service

# --- Rolling Update ---
kubectl set image deployment/order-service -n delivery-system order-service=order-service:v2
kubectl rollout status deployment/order-service -n delivery-system
kubectl rollout history deployment/order-service -n delivery-system
kubectl rollout undo deployment/order-service -n delivery-system

# --- Pod Deletion (self-healing test) ---
kubectl delete pod <pod-name> -n delivery-system
kubectl get pods -n delivery-system -w    # Watch recreation

# --- Access ---
kubectl port-forward svc/order-service 8001:8001 -n delivery-system

# --- Cleanup ---
kubectl delete namespace delivery-system
minikube stop
```

### 3.4 Rolling Update Process

```
State 1 (before):   [Pod-v1-A] [Pod-v1-B]         (2/2 ready)
                         ↓
Step 1: Create new:  [Pod-v1-A] [Pod-v1-B] [Pod-v2-C]  (maxSurge=1)
                         ↓
Step 2: v2-C ready:  [Pod-v1-A] [Pod-v1-B] [Pod-v2-C]  (3/3 ready)
                         ↓
Step 3: Remove v1-A:            [Pod-v1-B] [Pod-v2-C]  (2/2 ready)
                         ↓
Step 4: Create new:             [Pod-v1-B] [Pod-v2-C] [Pod-v2-D]
                         ↓
Step 5: Remove v1-B:                       [Pod-v2-C] [Pod-v2-D]
                         ↓
State 2 (after):    [Pod-v2-C] [Pod-v2-D]          (2/2 ready, zero downtime)
```

Commands executed:
```powershell
# Trigger rolling update
kubectl patch deployment order-service -n delivery-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"version":"v2"}}}}}'

# Monitor
kubectl rollout status deployment/order-service -n delivery-system
# Output: deployment "order-service" successfully rolled out

# Verify
kubectl get pods -n delivery-system -l app=order-service --show-labels
# Shows version=v2 on all pods
```

---

## 4. Testing

### 4.1 Availability Check

**Result:** All services responded successfully.
```
[STEP 1] Verifying service availability...
  OK  Order Service: ok
  OK  Courier Service: ok
  OK  Tracking Service: ok
  OK  Reporting Service: ok
```

**Method:** HTTP GET to `/health` endpoint on each service via port-forward.

**Inter-service communication verified:**
```
  OK  Order #9000 created
  OK  Courier #1 assigned, route: Маршрут від Центральний склад до Kubernetes Street 1
  OK  Status: В дорозі, Location: Центральний склад
```

**Redis caching verified:**
```
  Request 1 (cold): X-Cache: MISS
  Request 2 (warm): X-Cache: HIT
  Redis KEYS: cache:orders:list:limit=5:skip=0
```

### 4.2 Scaling

**Before scaling:**
```
NAME                             READY   STATUS    RESTARTS   AGE
order-service-544cd7f5cd-2mzg9   1/1     Running   0          17m
order-service-544cd7f5cd-4mxh8   1/1     Running   0          17m
```

**After `kubectl scale --replicas=4`:**
```
NAME                             READY   STATUS    RESTARTS   AGE
order-service-544cd7f5cd-2mzg9   1/1     Running   0          18m
order-service-544cd7f5cd-4mxh8   1/1     Running   0          18m
order-service-544cd7f5cd-fwcsq   1/1     Running   0          13s   ← NEW
order-service-544cd7f5cd-jcl4s   1/1     Running   0          13s   ← NEW
```

**Load balancing confirmed:**
```
Endpoints: 10.244.0.11:8001, 10.244.0.12:8001, 10.244.0.5:8001 + 1 more...
```
All 4 pod IPs registered as endpoints — K8s distributes traffic via kube-proxy.

### 4.3 Behavior When a Pod Stops

**Deleted pod:** `order-service-544cd7f5cd-2mzg9`

**Result:** Deployment controller immediately created a replacement pod:
```
NAME                             READY   STATUS    RESTARTS   AGE
order-service-544cd7f5cd-4mxh8   1/1     Running   0          20m
order-service-544cd7f5cd-fwcsq   1/1     Running   0          3m
order-service-544cd7f5cd-jcl4s   1/1     Running   0          3m
order-service-544cd7f5cd-xk9p2   1/1     Running   0          5s    ← REPLACEMENT
```

**Service remained accessible** — other 3 pods handled requests while the new pod was starting. Zero downtime.

---

## 5. Analysis

### 5.1 Comparison with Docker Compose

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Deployment scope** | Single host | Multi-node cluster |
| **Configuration** | `docker-compose.yml` | Multiple YAML manifests (separation of concerns) |
| **Scaling** | `--scale service=N` (manual, no LB) | `replicas: N` with built-in load balancing |
| **Self-healing** | `restart: always` (basic) | Deployment controller + liveness probes (intelligent) |
| **Updates** | Stop → Rebuild → Restart (downtime) | Rolling update (zero downtime) |
| **Rollback** | Not supported natively | `kubectl rollout undo` (instant) |
| **Service discovery** | Container name DNS | ClusterIP + CoreDNS (`svc.cluster.local`) |
| **Load balancing** | None (single container) | kube-proxy (iptables/IPVS rules) |
| **Resource control** | Optional `mem_limit` | Enforced requests/limits with QoS |
| **Health monitoring** | `healthcheck` (informational) | readiness (traffic) + liveness (restart) |
| **Storage** | Docker volumes (local) | PV/PVC (local, NFS, cloud) |
| **Secrets** | `.env` files (plaintext) | K8s Secrets (base64, can be encrypted) |
| **Networking** | Bridge network | Pod network (CNI) + Service network + Ingress |
| **CI/CD integration** | Limited | Native (ArgoCD, Flux, Helm) |
| **Observability** | `docker logs` | Prometheus, Grafana, built-in metrics |
| **Production use** | Development/testing | Production-grade |

### 5.2 Advantages of Orchestration

1. **High Availability** — Multiple replicas + automatic failover. Demonstrated: pod deleted, service stayed up with zero downtime.

2. **Horizontal Scaling** — Scale from 2 to 4 replicas in seconds. In production, Horizontal Pod Autoscaler (HPA) can auto-scale based on CPU/memory/custom metrics.

3. **Zero-Downtime Deployments** — Rolling updates replace pods gradually. `maxSurge: 1, maxUnavailable: 0` guarantees service capacity never drops below desired state.

4. **Self-Healing** — Deployment controller continuously reconciles actual state with desired state. Crashed pods are automatically replaced.

5. **Service Discovery & Load Balancing** — Services find each other by DNS name (`courier-service:8002`). kube-proxy distributes traffic evenly across all healthy pods.

6. **Resource Governance** — CPU/memory requests guarantee minimum resources; limits prevent runaway containers from affecting neighbors.

7. **Declarative Infrastructure as Code** — Entire system described in version-controlled YAML. `kubectl apply` brings cluster to desired state idempotently.

8. **Rollback Capability** — Every deployment change is recorded. One command reverts to any previous version.

### 5.3 Feasibility of Use

| Scenario | Recommendation |
|----------|---------------|
| Local development | Docker Compose (simpler, faster startup) |
| Team staging/QA | Kubernetes (shared cluster, namespaces per team) |
| Production (small scale) | Managed K8s (GKE, EKS, AKS) — reduces ops burden |
| Production (large scale) | Kubernetes — essential for scaling, reliability |
| CI/CD pipelines | Kubernetes — GitOps with ArgoCD/Flux |
| Microservices (>3 services) | Kubernetes — service mesh, observability |
| Monolith application | Docker Compose sufficient |

**For our Delivery System:**
- 5 microservices + Redis + shared database = **Kubernetes is justified**
- Inter-service communication, caching, scaling needs = orchestration provides clear value
- Production deployment would use managed Kubernetes (GKE/EKS/AKS) with:
  - PostgreSQL instead of SQLite (Cloud SQL / RDS)
  - Redis Cluster (Elasticache / Memorystore)
  - Ingress controller instead of NodePort
  - HPA for auto-scaling
  - Helm charts for templating

---

## 6. Conclusion

The Delivery System was successfully deployed to a local Kubernetes cluster (Minikube) with:
- 6 Deployments (5 services + Redis)
- 7 running Pods (order-service with 2 replicas)
- Full inter-service communication via K8s DNS
- Redis caching operational (X-Cache: HIT/MISS verified)
- Scaling tested: 2 → 4 replicas with load balancing
- Self-healing confirmed: pod deletion → automatic replacement
- Rolling update executed: v1 → v2 with zero downtime

Kubernetes provides significant advantages over Docker Compose for microservice architectures, particularly in availability, scalability, and operational reliability.
