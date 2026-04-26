# Delivery System — Microservices Architecture

## Services

| Service            | Port | Description                          |
|--------------------|------|--------------------------------------|
| **Frontend**       | 8000 | Static SPA (HTML/JS/CSS)             |
| **Order Service**  | 8001 | Orders CRUD, users, payment (Stripe) |
| **Courier Service**| 8002 | Couriers management & assignment     |
| **Tracking Service**| 8003 | Real-time order tracking             |
| **Reporting Service**| 8004 | Statistics & analytics reports      |

## Quick Start

```powershell
# 1. Install dependencies (once)
pip install fastapi uvicorn pydantic sqlalchemy stripe httpx aiofiles

# 2. Seed the database
python seed.py

# 3. Start all services
.\start_all.ps1
```

## Architecture

- All services share a single SQLite database (`shared/delivery.db`) for demo purposes
- **Order Service** calls **Courier Service** via HTTP (`httpx`) for courier assignment
- **Tracking Service** and **Reporting Service** are read-only consumers
- **Frontend** calls each service directly from the browser (CORS enabled)

## API Docs

Each service exposes Swagger UI at `/docs`:
- http://localhost:8001/docs — Order Service
- http://localhost:8002/docs — Courier Service
- http://localhost:8003/docs — Tracking Service
- http://localhost:8004/docs — Reporting Service
