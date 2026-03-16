from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from models.domain import Order, Courier, DeliveryStatus, UserCreate, UserResponse
from services.business_logic import DeliveryService
from sqlalchemy.orm import Session
from database import get_db, CourierDB, OrderDB, UserDB

router = APIRouter()

@router.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}

# --- Order Service ---
@router.post("/orders/", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order: Order, db: Session = Depends(get_db)):
    # 1. Перевіряємо, чи немає вже замовлення з таким ID
    existing_order = db.query(OrderDB).filter(OrderDB.id == order.id).first()
    if existing_order:
        raise HTTPException(status_code=400, detail="Order with this ID already exists")
    
    # 2. Створюємо запис для бази даних
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
    
    # 3. Зберігаємо в БД
    db.add(new_order)
    db.commit()
    db.refresh(new_order) # Оновлюємо об'єкт новими даними з БД (наприклад, згенерованими полями)
    
    return new_order

@router.get("/orders/", response_model=List[Order])
def get_all_orders(sort_by: Optional[str] = None, db: Session = Depends(get_db)):
    # Тепер ми беремо всі замовлення з бази даних SQLite!
    query = db.query(OrderDB)
    
    if sort_by:
        descending = sort_by.startswith('-')
        field_name = sort_by.lstrip('-') if descending else sort_by
        
        column = getattr(OrderDB, field_name, None)
        if column is not None:
            if descending:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            raise HTTPException(status_code=400, detail=f"Invalid sort field: {field_name}")

    return query.all()

@router.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    # Шукаємо замовлення за ID в базі
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/orders/{order_id}/status", response_model=Order)
def update_status(order_id: int, new_status: str, db: Session = Depends(get_db)):
    # 1. Знаходимо замовлення
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 2. Оновлюємо статус і зберігаємо зміни
    order.status = new_status
    db.commit()
    db.refresh(order)
    
    return order

@router.post("/orders/{order_id}/assign", response_model=Order)
def assign_courier(order_id: int, db: Session = Depends(get_db)):
    try:
        return DeliveryService.auto_assign_courier(order_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/orders/{order_id}/notify-arrival")
def notify_arrival(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status not in [DeliveryStatus.IN_TRANSIT.value, DeliveryStatus.ASSIGNED.value]:
        raise HTTPException(status_code=400, detail="Cannot notify arrival. Courier is not on the way.")
        
    order.status = DeliveryStatus.WAITING.value
    db.commit()
    db.refresh(order)
    
    message = f"Шановний {order.client_name}, ваш кур'єр очікує під дверима за адресою {order.client_address}!"
    return {"message": message, "order_status": order.status}

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db.delete(order)
    db.commit()

# --- Courier Service ---
@router.get("/couriers/", response_model=List[Courier])
def get_all_couriers(db: Session = Depends(get_db)):
    # Беремо всіх кур'єрів з бази
    couriers = db.query(CourierDB).all()
    return couriers

@router.delete("/couriers/{courier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = db.query(CourierDB).filter(CourierDB.id == courier_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    db.delete(courier)
    db.commit()

# --- Tracking Service ---
@router.get("/tracking/{order_id}")
def track_order(order_id: int, db: Session = Depends(get_db)):
    # 1. Шукаємо замовлення в базі даних SQLite
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    location = "Невідомо"
    
    # 2. Якщо замовленню призначено кур'єра, шукаємо його локацію в базі
    if order.courier_id:
        courier = db.query(CourierDB).filter(CourierDB.id == order.courier_id).first()
        if courier and courier.current_location:
            location = courier.current_location
            
    return {"order_id": order.id, "status": order.status, "current_location": location}

# --- Reporting Service ---
@router.get("/reports/deliveries")
def get_delivery_report(db: Session = Depends(get_db)):
    return DeliveryService.generate_report(db)

@router.get("/reports/daily")
def get_daily_statistics(date: str, db: Session = Depends(get_db)):
    # date in format YYYY-MM-DD
    try:
        return DeliveryService.get_daily_statistics(db, target_date=date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/reports/weekly")
def get_weekly_statistics(db: Session = Depends(get_db)):
    return DeliveryService.get_weekly_statistics(db)

# --- User Service ---
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    new_user = UserDB(
        name=user.name,
        email=user.email,
        password=user.password # В реальному проєкті пароль обов'язково треба хешувати
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
