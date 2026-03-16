from models.domain import Order, Courier, DeliveryStatus
from database import OrderDB, CourierDB
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict

class DeliveryService:
    @staticmethod
    def auto_assign_courier(order_id: int, db: Session) -> Order:
        order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != DeliveryStatus.CREATED:
            raise ValueError("Order is already assigned or in progress")

        # Знаходимо першого вільного кур'єра
        available_courier = db.query(CourierDB).filter(CourierDB.is_available == True).first()
        
        if not available_courier:
            raise Exception("No available couriers at the moment")

        # Оновлюємо стани
        available_courier.is_available = False
        order.courier_id = available_courier.id
        order.status = DeliveryStatus.ASSIGNED
        order.route = f"Маршрут від {available_courier.current_location} до {order.client_address}"
        
        db.commit()
        db.refresh(order)
        db.refresh(available_courier)
        
        return order

    @staticmethod
    def generate_report(db: Session) -> dict:
        total = db.query(OrderDB).count()
        delivered = db.query(OrderDB).filter(OrderDB.status == DeliveryStatus.DELIVERED.value).count()
        return {
            "total_orders": total,
            "delivered_orders": delivered,
            "pending_orders": total - delivered
        }

    @staticmethod
    def get_daily_statistics(db: Session, target_date: str) -> dict:
        try:
            # Парсимо дату з рядка YYYY-MM-DD
            dt = datetime.strptime(target_date, "%Y-%m-%d")
            start_of_day = datetime(dt.year, dt.month, dt.day)
            end_of_day = start_of_day + timedelta(days=1)
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")

        orders_today = db.query(OrderDB).filter(
            OrderDB.created_at >= start_of_day,
            OrderDB.created_at < end_of_day
        ).all()

        total_orders = len(orders_today)
        total_revenue = sum(o.price for o in orders_today if o.price)

        return {
            "date": target_date,
            "total_orders": total_orders,
            "total_revenue": total_revenue
        }

    @staticmethod
    def get_weekly_statistics(db: Session) -> dict:
        # Отримуємо статистику за останні 7 днів
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        orders_week = db.query(OrderDB).filter(
            OrderDB.created_at >= start_date,
            OrderDB.created_at <= end_date
        ).all()

        total_orders = len(orders_week)
        total_revenue = sum(o.price for o in orders_week if o.price)

        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "total_orders": total_orders,
            "total_revenue": total_revenue
        }