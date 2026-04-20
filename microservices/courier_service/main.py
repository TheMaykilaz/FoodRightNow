from fastapi import FastAPI, Depends, HTTPException
from typing import List
from models import Courier
from database import get_db, CourierDB, engine, Base
from sqlalchemy.orm import Session
import uvicorn
import redis
import json
import os

app = FastAPI(title="Courier Service API")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
cache = redis.from_url(REDIS_URL, decode_responses=True)

Base.metadata.create_all(bind=engine)

@app.get("/couriers/", response_model=List[Courier])
def get_all_couriers(db: Session = Depends(get_db)):
    return db.query(CourierDB).all()

@app.get("/couriers/available")
def get_available_couriers(db: Session = Depends(get_db)):
    try:
        cached_data = cache.get("couriers:available")
        if cached_data:
            return json.loads(cached_data)
    except redis.ConnectionError:
        print("Warning: Redis not connected. Falling back to DB.")

    couriers = db.query(CourierDB).filter(CourierDB.is_available == True).all()
    # Serialize for cache
    couriers_data = [{"id": c.id, "name": c.name, "is_available": c.is_available, "current_location": c.current_location} for c in couriers]
    
    try:
        cache.setex("couriers:available", 60, json.dumps(couriers_data))
    except redis.ConnectionError:
        pass
        
    return couriers

@app.post("/couriers/{courier_id}/assign")
def assign_courier(courier_id: int, client_address: str, db: Session = Depends(get_db)):
    courier = db.query(CourierDB).filter(CourierDB.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    if not courier.is_available:
        raise HTTPException(status_code=400, detail="Courier is not available")
    
    courier.is_available = False
    route = f"Маршрут від {courier.current_location} до {client_address}"
    db.commit()
    db.refresh(courier)
    
    # Invalidate Cache
    try:
        cache.delete("couriers:available")
    except redis.ConnectionError:
        pass
    
    return {"message": "Courier assigned", "courier": courier, "route": route}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
