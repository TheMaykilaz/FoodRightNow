from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
