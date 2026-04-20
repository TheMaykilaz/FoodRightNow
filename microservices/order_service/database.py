import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
