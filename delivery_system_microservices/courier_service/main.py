from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from database import get_db, CourierDB, create_tables
from models import Courier, AssignOrderRequest

app = FastAPI(title="Courier Service", version="1.0.0")

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


@app.on_event("startup")
def on_startup():
    create_tables()


@app.get("/health", tags=["system"])
def health_check():
    return {"service": "courier_service", "status": "ok"}


@app.get("/couriers/", response_model=List[Courier])
def get_all_couriers(db: Session = Depends(get_db)):
    return db.query(CourierDB).all()


@app.get("/couriers/{courier_id}", response_model=Courier)
def get_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = db.query(CourierDB).filter(CourierDB.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    return courier


@app.post("/couriers/assign-order")
def assign_order_to_courier(request: AssignOrderRequest, db: Session = Depends(get_db)):
    available_courier = db.query(CourierDB).filter(CourierDB.is_available == True).first()
    if not available_courier:
        raise HTTPException(status_code=404, detail="Немає вільних кур'єрів")

    available_courier.is_available = False
    available_courier.current_order_id = request.order_id
    available_courier.destination = request.order_address

    route = f"Маршрут від {available_courier.current_location} до {request.order_address}"

    db.commit()
    db.refresh(available_courier)

    return {
        "courier_id": available_courier.id,
        "courier_name": available_courier.name,
        "route": route
    }


@app.post("/couriers/{courier_id}/free", status_code=status.HTTP_204_NO_CONTENT)
def free_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = db.query(CourierDB).filter(CourierDB.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    courier.is_available = True
    courier.current_order_id = None
    courier.destination = None
    db.commit()


@app.delete("/couriers/{courier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = db.query(CourierDB).filter(CourierDB.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    db.delete(courier)
    db.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
