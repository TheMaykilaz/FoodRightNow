import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shared', 'delivery.db'))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String)
    client_phone = Column(String)
    client_address = Column(String)
    status = Column(String)
    courier_id = Column(Integer, nullable=True)
    route = Column(String, nullable=True)
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CourierDB(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    is_available = Column(Boolean, default=True)
    current_location = Column(String, default="База")
    current_order_id = Column(Integer, nullable=True)
    destination = Column(String, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
