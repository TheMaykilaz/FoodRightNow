from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from database import get_db, OrderDB, CourierDB
from cache import cacheable

DELIVERED = "Доставлено"
CANCELLED = "Скасовано"

app = FastAPI(title="Reporting Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_error_format(status_code: int, message: str, path: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status_code,
            "message": message,
            "path": path
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return create_error_format(exc.status_code, exc.detail, request.url.path)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return create_error_format(422, "Помилка валідації даних", request.url.path)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return create_error_format(500, "Внутрішня помилка сервера", request.url.path)


@app.get("/health", tags=["system"])
def health_check():
    return {"service": "reporting_service", "status": "ok"}


@app.get("/reports/deliveries")
@cacheable("reports:deliveries", ttl=30)
def get_delivery_report(db: Session = Depends(get_db)):
    total = db.query(OrderDB).count()
    delivered = db.query(OrderDB).filter(OrderDB.status == DELIVERED).count()
    cancelled = db.query(OrderDB).filter(OrderDB.status == CANCELLED).count()

    all_prices = [o.price for o in db.query(OrderDB).all() if o.price]
    avg_price = sum(all_prices) / len(all_prices) if all_prices else 0.0

    return {
        "total_orders": total,
        "delivered_orders": delivered,
        "cancelled_orders": cancelled,
        "pending_orders": total - delivered - cancelled,
        "average_order_price": round(avg_price, 2)
    }


@app.get("/reports/daily")
@cacheable("reports:daily", ttl=60)
def get_daily_statistics(date: str, db: Session = Depends(get_db)):
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        start_of_day = datetime(dt.year, dt.month, dt.day)
        end_of_day = start_of_day + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    orders_today = db.query(OrderDB).filter(
        OrderDB.created_at >= start_of_day,
        OrderDB.created_at < end_of_day
    ).all()

    total_orders = len(orders_today)
    delivered_orders = len([o for o in orders_today if o.status == DELIVERED])
    cancelled_orders = len([o for o in orders_today if o.status == CANCELLED])
    total_revenue = sum(o.price for o in orders_today if o.price and o.status != CANCELLED)
    avg_price = total_revenue / total_orders if total_orders > 0 else 0.0

    return {
        "date": date,
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": round(total_revenue, 2),
        "average_order_price": round(avg_price, 2)
    }


@app.get("/reports/weekly")
@cacheable("reports:weekly", ttl=30)
def get_weekly_statistics(db: Session = Depends(get_db)):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    orders_week = db.query(OrderDB).filter(
        OrderDB.created_at >= start_date,
        OrderDB.created_at <= end_date
    ).all()

    total_orders = len(orders_week)
    delivered_orders = len([o for o in orders_week if o.status == DELIVERED])
    cancelled_orders = len([o for o in orders_week if o.status == CANCELLED])
    total_revenue = sum(o.price for o in orders_week if o.price and o.status != CANCELLED)
    active_couriers = len(set(o.courier_id for o in orders_week if o.courier_id))

    return {
        "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": round(total_revenue, 2),
        "active_couriers_count": active_couriers
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
