import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta, timezone

SHARED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared')
os.makedirs(SHARED_DIR, exist_ok=True)
DB_PATH = os.path.join(SHARED_DIR, 'delivery.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)


class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client_name = Column(String)
    client_phone = Column(String)
    client_address = Column(String)
    status = Column(String, default="Очікує оплати")
    courier_id = Column(Integer, nullable=True)
    route = Column(String, nullable=True)
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    client = relationship("UserDB", foreign_keys=[client_id])


class CourierDB(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_available = Column(Boolean, default=True)
    current_location = Column(String, default="База")
    current_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    destination = Column(String, nullable=True)
    current_order = relationship("OrderDB", foreign_keys=[current_order_id])


def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    couriers = [
        CourierDB(id=1, name="Олександр", is_available=True, current_location="Центральний склад"),
        CourierDB(id=2, name="Марія", is_available=False, current_location="Вул. Наукова, 10", current_order_id=104, destination="Вул. Стрийська, 100"),
        CourierDB(id=3, name="Василь", is_available=True, current_location="Південний склад"),
        CourierDB(id=4, name="Ірина", is_available=False, current_location="Південний склад", current_order_id=105, destination="Вул. Коперника, 15"),
        CourierDB(id=5, name="Андрій", is_available=True, current_location="Пл. Ринок, 1"),
        CourierDB(id=6, name="Оксана", is_available=True, current_location="Північний склад"),
    ]

    users = [
        UserDB(id=1, name="Зареєстрований Юзер", email="user@gmail.com", password="password123", phone="+380998887766", address="Вул. Зареєстрована, 55"),
        UserDB(id=2, name="Іван Іванов", email="ivan@gmail.com", password="password123", phone="+380501112233", address="Пл. Ринок, 10"),
        UserDB(id=3, name="Петро Сидоренко", email="petro@gmail.com", password="password123", phone="+380631112255", address="Вул. Франка, 5"),
        UserDB(id=4, name="Вікторія Ткаченко", email="vika@gmail.com", password="password123", phone="+380671112288", address="Вул. Зелена, 40"),
        UserDB(id=5, name="Олена Коваленко", email="olena@gmail.com", password="password123", phone="+380671112244", address="Вул. Стрийська, 100"),
        UserDB(id=6, name="Софія Кравченко", email="sofia@gmail.com", password="password123", phone="+380991112300", address="Вул. Коперника, 15"),
        UserDB(id=7, name="Тарас Шевчук", email="taras@gmail.com", password="password123", phone="+380631112299", address="Вул. Личаківська, 33"),
        UserDB(id=8, name="Анна Бойко", email="anna@gmail.com", password="password123", phone="+380991112266", address="Просп. Свободи, 20"),
        UserDB(id=9, name="Дмитро Мельник", email="dmytro@gmail.com", password="password123", phone="+380501112277", address="Вул. Городоцька, 150"),
        UserDB(id=10, name="Юлія Лисенко", email="yulia@gmail.com", password="password123", phone="+380661112233", address="Вул. Чорновола, 45"),
        UserDB(id=11, name="Валентин Зінченко", email="valentin@gmail.com", password="password123", phone="+380671234567", address="Вул. Кн. Ольги, 114"),
        UserDB(id=12, name="Марина Козачок", email="maryna@gmail.com", password="password123", phone="+380931122334", address="Вул. Підвальна, 9"),
        UserDB(id=13, name="Олег Попенко", email="oleg@gmail.com", password="password123", phone="+380998877665", address="Вул. Чупринки, 85"),
    ]

    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    last_week = today - timedelta(days=5)

    orders = [
        OrderDB(id=100, client_id=1, client_name="Зареєстрований Юзер", client_phone="+380998887766", client_address="Вул. Зареєстрована, 55", status="Створено", price=550.00, created_at=today),
        OrderDB(id=101, client_id=2, client_name="Іван Іванов", client_phone="+380501112233", client_address="Пл. Ринок, 10", status="Створено", price=150.50, created_at=today),
        OrderDB(id=102, client_id=3, client_name="Петро Сидоренко", client_phone="+380631112255", client_address="Вул. Франка, 5", status="Створено", price=300.20, created_at=today),
        OrderDB(id=103, client_id=4, client_name="Вікторія Ткаченко", client_phone="+380671112288", client_address="Вул. Зелена, 40", status="Створено", price=55.00, created_at=today),
        OrderDB(id=104, client_id=5, client_name="Олена Коваленко", client_phone="+380671112244", client_address="Вул. Стрийська, 100", status="В дорозі", courier_id=2, route="Центральний склад -> Вул. Стрийська, 100", price=450.00, created_at=today),
        OrderDB(id=105, client_id=6, client_name="Софія Кравченко", client_phone="+380991112300", client_address="Вул. Коперника, 15", status="В дорозі", courier_id=4, route="Південний склад -> Вул. Коперника, 15", price=89.90, created_at=yesterday),
        OrderDB(id=106, client_id=7, client_name="Тарас Шевчук", client_phone="+380631112299", client_address="Вул. Личаківська, 33", status="Призначено кур'єра", courier_id=2, route="Вул. Наукова, 10 -> Вул. Личаківська, 33", price=210.00, created_at=yesterday),
        OrderDB(id=107, client_id=8, client_name="Анна Бойко", client_phone="+380991112266", client_address="Просп. Свободи, 20", status="Доставлено", courier_id=6, route="Північний склад -> Просп. Свободи, 20", price=1000.00, created_at=two_days_ago),
        OrderDB(id=108, client_id=9, client_name="Дмитро Мельник", client_phone="+380501112277", client_address="Вул. Городоцька, 150", status="Скасовано", price=120.00, created_at=two_days_ago),
        OrderDB(id=109, client_id=10, client_name="Юлія Лисенко", client_phone="+380661112233", client_address="Вул. Чорновола, 45", status="Доставлено", courier_id=3, route="Південний склад -> Вул. Чорновола, 45", price=400.00, created_at=today),
        OrderDB(id=110, client_id=11, client_name="Валентин Зінченко", client_phone="+380671234567", client_address="Вул. Кн. Ольги, 114", status="Доставлено", courier_id=5, route="Пл. Ринок, 1 -> Вул. Кн. Ольги, 114", price=890.50, created_at=last_week),
        OrderDB(id=111, client_id=12, client_name="Марина Козачок", client_phone="+380931122334", client_address="Вул. Підвальна, 9", status="Скасовано", price=45.00, created_at=yesterday),
        OrderDB(id=112, client_id=13, client_name="Олег Попенко", client_phone="+380998877665", client_address="Вул. Чупринки, 85", status="Доставлено", courier_id=1, route="Центральний склад -> Вул. Чупринки, 85", price=320.00, created_at=yesterday),
    ]

    db.add_all(users)
    db.add_all(couriers + orders)
    db.commit()
    db.close()

    print(f"Database seeded at: {DB_PATH}")
    print("Added: 13 users, 6 couriers, 13 orders")


if __name__ == "__main__":
    seed_database()
