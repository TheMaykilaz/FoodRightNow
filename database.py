from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker

# Вказуємо файл бази даних SQLite, який буде створено в папці проєкту
SQLALCHEMY_DATABASE_URL = "sqlite:///./delivery.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Моделі таблиць бази даних ---
class CourierDB(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_available = Column(Boolean, default=True)
    current_location = Column(String, default="База")

class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String)
    client_phone = Column(String)
    client_address = Column(String)
    status = Column(String, default="Створено")
    courier_id = Column(Integer, nullable=True)
    route = Column(String, nullable=True)
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)

# Залежність для FastAPI, яка відкриває і закриває сесію БД для кожного запиту
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()