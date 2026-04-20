from fastapi import FastAPI, Depends, HTTPException, status
from typing import List
from models import Order
from database import get_db, OrderDB, engine, Base
from sqlalchemy.orm import Session
import httpx
import uvicorn

app = FastAPI(title="Order Service API")

Base.metadata.create_all(bind=engine)

COURIER_SERVICE_URL = "http://localhost:8002"

@app.post("/orders/", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order: Order, db: Session = Depends(get_db)):
    existing_order = db.query(OrderDB).filter(OrderDB.id == order.id).first()
    if existing_order:
        raise HTTPException(status_code=400, detail="Order with this ID already exists")
    
    new_order = OrderDB(
        id=order.id,
        client_name=order.client_name,
        client_phone=order.client_phone,
        client_address=order.client_address,
        status=order.status,
        courier_id=order.courier_id,
        route=order.route,
        price=order.price,
        created_at=order.created_at
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.get("/orders/", response_model=List[Order])
def get_all_orders(db: Session = Depends(get_db)):
    return db.query(OrderDB).all()

@app.post("/orders/{order_id}/assign", response_model=Order)
def assign_courier(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status != "Створено":
        raise HTTPException(status_code=400, detail="Order already assigned or in progress")

    try:
        # Step 1: Find available courier by calling Courier Service
        response = httpx.get(f"{COURIER_SERVICE_URL}/couriers/available")
        response.raise_for_status()
        available_couriers = response.json()
        
        if not available_couriers:
            raise HTTPException(status_code=409, detail="No available couriers at the moment")
            
        selected_courier = available_couriers[0]
        
        # Step 2: Assign task to courier over HTTP
        assign_resp = httpx.post(f"{COURIER_SERVICE_URL}/couriers/{selected_courier['id']}/assign", params={"client_address": order.client_address})
        assign_resp.raise_for_status()
        assign_data = assign_resp.json()
        
        # Step 3: Update local order locally
        order.courier_id = selected_courier['id']
        order.status = "Призначено кур'єра"
        order.route = assign_data['route']
        db.commit()
        db.refresh(order)
        
        return order

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Courier service is unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Courier service error: {e.response.text}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
