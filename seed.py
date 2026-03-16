from database import engine, Base, SessionLocal, CourierDB, OrderDB
from datetime import datetime, timedelta

def seed_database():
    # Очищаємо всі таблиці перед новим записом і створюємо їх
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Створюємо розширений список кур'єрів
    couriers = [
        CourierDB(id=1, name="Олександр", is_available=True, current_location="Центральний склад"),
        CourierDB(id=2, name="Марія", is_available=False, current_location="Вул. Наукова, 10"),
        CourierDB(id=3, name="Василь", is_available=True, current_location="Південний склад"),
        CourierDB(id=4, name="Ірина", is_available=False, current_location="Вул. Сихівська, 22"),
        CourierDB(id=5, name="Андрій", is_available=True, current_location="Пл. Ринок, 1"),
        CourierDB(id=6, name="Оксана", is_available=True, current_location="Північний склад"),
    ]

    # Генеруємо дати (сьогодні, вчора, позавчора)
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # 2. Створюємо різноманітні замовлення з різними статусами
    orders = [
        # Нові замовлення, які очікують призначення (Сьогодні)
        OrderDB(id=101, client_name="Іван Іванов", client_phone="+380501112233", client_address="Пл. Ринок, 10", status="Створено", price=150.50, created_at=today),
        OrderDB(id=102, client_name="Петро Сидоренко", client_phone="+380631112255", client_address="Вул. Франка, 5", status="Створено", price=300.20, created_at=today),
        OrderDB(id=103, client_name="Вікторія Ткаченко", client_phone="+380671112288", client_address="Вул. Зелена, 40", status="Створено", price=55.00, created_at=today),
        
        # Замовлення в процесі доставки (Сьогодні/Вчора)
        OrderDB(id=104, client_name="Олена Коваленко", client_phone="+380671112244", client_address="Вул. Стрийська, 100", status="В дорозі", courier_id=2, route="Центральний склад -> Вул. Стрийська, 100", price=450.00, created_at=today),
        OrderDB(id=105, client_name="Софія Кравченко", client_phone="+380991112300", client_address="Вул. Коперника, 15", status="В дорозі", courier_id=4, route="Південний склад -> Вул. Коперника, 15", price=89.90, created_at=yesterday),
        
        # Замовлення, яким щойно призначили кур'єра, але вони ще не виїхали
        OrderDB(id=106, client_name="Тарас Шевчук", client_phone="+380631112299", client_address="Вул. Личаківська, 33", status="Призначено кур'єра", courier_id=2, route="Вул. Наукова, 10 -> Вул. Личаківська, 33", price=210.00, created_at=yesterday),
        
        # Завершені та скасовані замовлення для перевірки звітів (Позавчора)
        OrderDB(id=107, client_name="Анна Бойко", client_phone="+380991112266", client_address="Просп. Свободи, 20", status="Доставлено", courier_id=6, route="Північний склад -> Просп. Свободи, 20", price=1000.00, created_at=two_days_ago),
        OrderDB(id=108, client_name="Дмитро Мельник", client_phone="+380501112277", client_address="Вул. Городоцька, 150", status="Скасовано", price=120.00, created_at=two_days_ago),
        OrderDB(id=109, client_name="Юлія Лисенко", client_phone="+380661112233", client_address="Вул. Чорновола, 45", status="Доставлено", courier_id=3, route="Південний склад -> Вул. Чорновола, 45", price=400.00, created_at=two_days_ago),
    ]

    # Додаємо всі записи в сесію та зберігаємо
    db.add_all(couriers + orders)
    db.commit()
    db.close()

    print("Базу SQLite (delivery.db) успішно оновлено! Додано 6 кур'єрів та 9 замовлень з розширеною статистикою (ціни, дати).")

if __name__ == "__main__":
    seed_database()