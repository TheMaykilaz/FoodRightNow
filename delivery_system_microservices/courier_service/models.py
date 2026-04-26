from pydantic import BaseModel
from typing import Optional


class Courier(BaseModel):
    id: int
    name: str
    is_available: bool = True
    current_location: Optional[str] = "База"
    current_order_id: Optional[int] = None
    destination: Optional[str] = None

    class Config:
        from_attributes = True


class AssignOrderRequest(BaseModel):
    order_id: int
    order_address: str
