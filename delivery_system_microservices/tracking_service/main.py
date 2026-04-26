from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database import get_db, OrderDB, CourierDB

app = FastAPI(title="Tracking Service", version="1.0.0")

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
    return {"service": "tracking_service", "status": "ok"}


@app.get("/tracking/{order_id}")
def track_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    location = "Невідомо"
    courier_name = None

    if order.courier_id:
        courier = db.query(CourierDB).filter(CourierDB.id == order.courier_id).first()
        if courier:
            location = courier.current_location or "Невідомо"
            courier_name = courier.name

    return {
        "order_id": order.id,
        "status": order.status,
        "current_location": location,
        "courier_name": courier_name,
        "route": order.route,
        "client_address": order.client_address
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
