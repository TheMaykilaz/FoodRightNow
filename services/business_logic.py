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
        
        if order.status == DeliveryStatus.AWAITING_PAYMENT:
            raise ValueError("Замовлення очікує оплати. Спочатку проведіть оплату.")
            
        if order.status != DeliveryStatus.CREATED:
            raise ValueError("Order is already assigned or in progress")

        # Знаходимо першого вільного кур'єра
        available_courier = db.query(CourierDB).filter(CourierDB.is_available == True).first()
        
        if not available_courier:
            raise Exception("No available couriers at the moment")

        # Оновлюємо стани
        available_courier.is_available = False
        available_courier.current_order_id = order.id
        available_courier.destination = order.client_address
        
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
        cancelled = db.query(OrderDB).filter(OrderDB.status == DeliveryStatus.CANCELLED.value).count()
        
        all_prices = [o.price for o in db.query(OrderDB).all() if o.price]
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0.0

        return {
            "total_orders": total,
            "delivered_orders": delivered,
            "cancelled_orders": cancelled,
            "pending_orders": total - delivered - cancelled,
            "average_order_price": round(avg_price, 2)
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
        delivered_orders = len([o for o in orders_today if o.status == DeliveryStatus.DELIVERED.value])
        cancelled_orders = len([o for o in orders_today if o.status == DeliveryStatus.CANCELLED.value])
        
        total_revenue = sum(o.price for o in orders_today if o.price and o.status != DeliveryStatus.CANCELLED.value)
        avg_price = total_revenue / total_orders if total_orders > 0 else 0.0

        return {
            "date": target_date,
            "total_orders": total_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": round(total_revenue, 2),
            "average_order_price": round(avg_price, 2)
        }

    @staticmethod
    def get_weekly_statistics(db: Session) -> dict:
        # Отримуємо статистику за останні 7 днів
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        orders_week = db.query(OrderDB).filter(
            OrderDB.created_at >= start_date,
            OrderDB.created_at <= end_date
        ).all()

        total_orders = len(orders_week)
        delivered_orders = len([o for o in orders_week if o.status == DeliveryStatus.DELIVERED.value])
        cancelled_orders = len([o for o in orders_week if o.status == DeliveryStatus.CANCELLED.value])

        total_revenue = sum(o.price for o in orders_week if o.price and o.status != DeliveryStatus.CANCELLED.value)
        
        # Кількість унікальних кур'єрів, які доставляли на цьому тижні
        active_couriers = len(set(o.courier_id for o in orders_week if o.courier_id))

        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "total_orders": total_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": round(total_revenue, 2),
            "active_couriers_count": active_couriers
        }