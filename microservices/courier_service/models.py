from pydantic import BaseModel
from typing import Optional

class Courier(BaseModel):
    id: int
    name: str
    is_available: bool = True
    current_location: Optional[str] = "База"

    class Config:
        from_attributes = True
