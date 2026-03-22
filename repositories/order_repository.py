from sqlalchemy.orm import Session
from database import OrderDB
from typing import Optional

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[OrderDB]:
        return self.db.query(OrderDB).filter(OrderDB.id == order_id).first()

    def get_all(self, skip: int = 0, limit: int = 10, status_filter: Optional[str] = None, sort_by: Optional[str] = None):
        query = self.db.query(OrderDB)
        
        # Фільтрація
        if status_filter:
            query = query.filter(OrderDB.status == status_filter)
            
        # Сортування
        if sort_by:
            descending = sort_by.startswith('-')
            field_name = sort_by.lstrip('-') if descending else sort_by
            
            column = getattr(OrderDB, field_name, None)
            if column is not None:
                if descending:
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
        else:
            # За замовчуванням: від найновіших
            query = query.order_by(OrderDB.id.desc())

        # Пагінація
        return query.offset(skip).limit(limit).all()

    def create(self, order_data: dict) -> OrderDB:
        new_order = OrderDB(**order_data)
        self.db.add(new_order)
        self.db.commit()
        self.db.refresh(new_order)
        return new_order

    def update(self, order_id: int, update_data: dict) -> Optional[OrderDB]:
        order = self.get_by_id(order_id)
        if not order:
            return None
            
        for key, value in update_data.items():
            setattr(order, key, value)
            
        self.db.commit()
        self.db.refresh(order)
        return order
        
    def delete(self, order_id: int) -> bool:
        order = self.get_by_id(order_id)
        if not order:
            return False
            
        self.db.delete(order)
        self.db.commit()
        return True
