# ============================================================
#  Kubernetes Deployment Script for Delivery System
#  Prerequisites: Minikube installed + running
# ============================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Delivery System - Kubernetes Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- Step 1: Start Minikube (if not running) ---
Write-Host "`n[1/7] Checking Minikube status..." -ForegroundColor Yellow
$minikubeStatus = minikube status --format='{{.Host}}' 2>$null
if ($minikubeStatus -ne "Running") {
    Write-Host "  Starting Minikube..." -ForegroundColor Gray
    minikube start --driver=docker --memory=4096 --cpus=2
} else {
    Write-Host "  Minikube is already running." -ForegroundColor Green
}

# --- Step 2: Configure Docker to use Minikube's daemon ---
Write-Host "`n[2/7] Configuring Docker environment for Minikube..." -ForegroundColor Yellow
& minikube -p minikube docker-env --shell powershell | Invoke-Expression

# --- Step 3: Build Docker images inside Minikube ---
Write-Host "`n[3/7] Building Docker images..." -ForegroundColor Yellow
$root = Split-Path -Parent $PSScriptRoot

docker build -t order-service:latest "$root\order_service"
docker build -t courier-service:latest "$root\courier_service"
docker build -t tracking-service:latest "$root\tracking_service"
docker build -t reporting-service:latest "$root\reporting_service"
docker build -t frontend-service:latest "$root\frontend"
docker build -t delivery-seed:latest -f "$root\Dockerfile.seed" "$root"

Write-Host "  All images built successfully." -ForegroundColor Green

# --- Step 4: Create namespace and config ---
Write-Host "`n[4/7] Creating namespace and ConfigMap..." -ForegroundColor Yellow
kubectl apply -f "$PSScriptRoot\namespace.yaml"
kubectl apply -f "$PSScriptRoot\configmap.yaml"

# --- Step 5: Deploy Redis + Database volume ---
Write-Host "`n[5/7] Deploying Redis and database storage..." -ForegroundColor Yellow
kubectl apply -f "$PSScriptRoot\pv-database.yaml"
kubectl apply -f "$PSScriptRoot\redis-deployment.yaml"
kubectl apply -f "$PSScriptRoot\redis-service.yaml"

Write-Host "  Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n delivery-system --timeout=60s

# --- Step 6: Run database seed job ---
Write-Host "`n[6/7] Running database seed job..." -ForegroundColor Yellow
kubectl delete job db-seed -n delivery-system 2>$null
kubectl apply -f "$PSScriptRoot\seed-job.yaml"
kubectl wait --for=condition=complete job/db-seed -n delivery-system --timeout=60s
Write-Host "  Database seeded successfully." -ForegroundColor Green

# --- Step 7: Deploy all services ---
Write-Host "`n[7/7] Deploying microservices..." -ForegroundColor Yellow
kubectl apply -f "$PSScriptRoot\order-service-deployment.yaml"
kubectl apply -f "$PSScriptRoot\order-service-svc.yaml"
kubectl apply -f "$PSScriptRoot\courier-service-deployment.yaml"
kubectl apply -f "$PSScriptRoot\courier-service-svc.yaml"
kubectl apply -f "$PSScriptRoot\tracking-service-deployment.yaml"
kubectl apply -f "$PSScriptRoot\tracking-service-svc.yaml"
kubectl apply -f "$PSScriptRoot\reporting-service-deployment.yaml"
kubectl apply -f "$PSScriptRoot\reporting-service-svc.yaml"
kubectl apply -f "$PSScriptRoot\frontend-deployment.yaml"
kubectl apply -f "$PSScriptRoot\frontend-svc.yaml"

Write-Host "`n  Waiting for all pods to be ready..."
kubectl wait --for=condition=ready pod -l app=order-service -n delivery-system --timeout=90s
kubectl wait --for=condition=ready pod -l app=courier-service -n delivery-system --timeout=90s
kubectl wait --for=condition=ready pod -l app=tracking-service -n delivery-system --timeout=90s
kubectl wait --for=condition=ready pod -l app=reporting-service -n delivery-system --timeout=90s
kubectl wait --for=condition=ready pod -l app=frontend -n delivery-system --timeout=90s

# --- Done ---
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Pods:" -ForegroundColor Cyan
kubectl get pods -n delivery-system -o wide
Write-Host ""
Write-Host "  Services:" -ForegroundColor Cyan
kubectl get services -n delivery-system
Write-Host ""

$minikubeIp = minikube ip
Write-Host "  Access URLs:" -ForegroundColor Cyan
Write-Host "    Frontend:   http://${minikubeIp}:30000"
Write-Host "    Orders:     http://${minikubeIp}:30001/docs"
Write-Host "    Couriers:   http://${minikubeIp}:30002/docs"
Write-Host "    Tracking:   http://${minikubeIp}:30003/docs"
Write-Host "    Reporting:  http://${minikubeIp}:30004/docs"
Write-Host ""
Write-Host "  Or use: minikube service frontend-service -n delivery-system" -ForegroundColor Gray
