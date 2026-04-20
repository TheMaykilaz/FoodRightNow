import os
import sys
from datetime import datetime

# Configure module paths dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def seed_couriers():
    os.chdir(os.path.join(BASE_DIR, 'courier_service'))
    sys.path.insert(0, os.path.join(BASE_DIR, 'courier_service'))
    import database as courier_db
    courier_db.Base.metadata.drop_all(bind=courier_db.engine)
    courier_db.Base.metadata.create_all(bind=courier_db.engine)

    db = courier_db.SessionLocal()
    couriers = [
        courier_db.CourierDB(id=1, name="Олександр", is_available=True, current_location="Центральний склад"),
        courier_db.CourierDB(id=2, name="Марія", is_available=False, current_location="Вул. Наукова, 10"),
        courier_db.CourierDB(id=3, name="Василь", is_available=True, current_location="Південний склад"),
    ]
    db.add_all(couriers)
    db.commit()
    db.close()
    sys.path.pop(0)

def seed_orders():
    os.chdir(os.path.join(BASE_DIR, 'order_service'))
    sys.path.insert(0, os.path.join(BASE_DIR, 'order_service'))
    if 'database' in sys.modules:
        del sys.modules['database']
    import database as order_db
    order_db.Base.metadata.drop_all(bind=order_db.engine)
    order_db.Base.metadata.create_all(bind=order_db.engine)

    db = order_db.SessionLocal()
    orders = [
        order_db.OrderDB(id=101, client_name="Іван Іванов", client_phone="+380501112233", client_address="Пл. Ринок, 10", status="Створено", price=150.50, created_at=datetime.utcnow()),
        order_db.OrderDB(id=102, client_name="Петро Сидоренко", client_phone="+380631112255", client_address="Вул. Франка, 5", status="Створено", price=300.20, created_at=datetime.utcnow())
    ]
    db.add_all(orders)
    db.commit()
    db.close()
    sys.path.pop(0)

if __name__ == "__main__":
    seed_couriers()
    seed_orders()
    print("Databases for microservices successfully created and seeded!")
