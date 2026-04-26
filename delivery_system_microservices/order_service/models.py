from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional
from datetime import datetime
import re


class DeliveryStatus(str, Enum):
    AWAITING_PAYMENT = "Очікує оплати"
    CREATED = "Створено"
    ASSIGNED = "Призначено кур'єра"
    IN_TRANSIT = "В дорозі"
    WAITING = "Кур'єр очікує"
    DELIVERED = "Доставлено"
    CANCELLED = "Скасовано"


class Order(BaseModel):
    id: int
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_address: Optional[str] = None
    status: str = "Очікує оплати"
    courier_id: Optional[int] = None
    route: Optional[str] = None
    price: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None
    address: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v.endswith('@gmail.com'):
            raise ValueError('Дозволена тільки пошта @gmail.com')
        if not re.match(r'^[\w\.-]+@gmail\.com$', v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^\+380\d{9}$', v) and not re.match(r'^\d{9}$', v):
                raise ValueError('Номер телефону повинен містити 9 цифр (або бути у форматі +380XXXXXXXXX)')
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
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True
