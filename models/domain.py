from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime

class DeliveryStatus(str, Enum):
    CREATED = "Створено"
    ASSIGNED = "Призначено кур'єра"
    IN_TRANSIT = "В дорозі"
    WAITING = "Кур'єр очікує"
    DELIVERED = "Доставлено"
    CANCELLED = "Скасовано"

class Client(BaseModel):
    name: str = Field(..., min_length=2)
    phone: str
    address: str

class Courier(BaseModel):
    id: int
    name: str
    is_available: bool = True
    current_location: Optional[str] = "База"

    class Config:
        from_attributes = True  

class Order(BaseModel):
    id: int
    client_name: str
    client_phone: str
    client_address: str
    status: str = "Створено"
    courier_id: Optional[int] = None
    route: Optional[str] = None
    price: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

import re
from pydantic import field_validator

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    password: str = Field(..., min_length=8)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True