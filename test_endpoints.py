from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    print("Health OK")

def test_sorting():
    response = client.get("/orders/?sort_by=-price")
    assert response.status_code == 200
    data = response.json()
    prices = [o["price"] for o in data]
    print(prices)
    assert prices == sorted(prices, reverse=True)
    
    response = client.get("/orders/?sort_by=price")
    data = response.json()
    prices_asc = [o["price"] for o in data]
    assert prices_asc == sorted(prices)
    print("Sorting OK")
    
def test_user_creation():
    import uuid
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    user_data = {
        "name": "Test User",
        "email": email,
        "password": "Password123"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201
    print("User Creation OK")
    
    # duplicate
    response = client.post("/users/", json=user_data)
    assert response.status_code == 400
    print("User Duplicate Email check OK")
    
    # invalid email
    user_data["email"] = "invalid_email"
    response = client.post("/users/", json=user_data)
    assert response.status_code == 422
    print("User Invalid Email check OK")
    
    # invalid password (too short)
    user_data["email"] = f"test2_{uuid.uuid4().hex[:6]}@example.com"
    user_data["password"] = "short"
    response = client.post("/users/", json=user_data)
    assert response.status_code == 422
    print("User Invalid Password (short) check OK")

    # invalid password (no letters)
    user_data["password"] = "123456789"
    response = client.post("/users/", json=user_data)
    assert response.status_code == 422
    print("User Invalid Password (no letters) check OK")

    # invalid password (no numbers)
    user_data["password"] = "Password"
    response = client.post("/users/", json=user_data)
    assert response.status_code == 422
    print("User Invalid Password (no numbers) check OK")

def test_delete_endpoints():
    # 1. Створюємо та видаляємо замовлення
    order_data = {
        "id": 9999,
        "client_name": "Test Delete",
        "client_phone": "+380501234567",
        "client_address": "Test Address"
    }
    client.post("/orders/", json=order_data)
    
    del_order_resp = client.delete("/orders/9999")
    assert del_order_resp.status_code == 204
    
    del_order_resp_404 = client.delete("/orders/9999")
    assert del_order_resp_404.status_code == 404
    print("Delete Order OK")

    # 2. Видаляємо кур'єра
    # Для цього тесту припустимо, що у нас є створений seed-скриптом кур'єр з id=1
    del_courier_resp = client.delete("/couriers/1")
    assert del_courier_resp.status_code == 204
    print("Delete Courier OK")

    # 3. Створюємо і видаляємо користувача
    import uuid
    email = f"test_del_{uuid.uuid4().hex[:6]}@example.com"
    user_data = {
        "name": "Test Delete User",
        "email": email,
        "password": "Password123"
    }
    create_resp = client.post("/users/", json=user_data)
    user_id = create_resp.json()["id"]
    
    
    del_user_resp = client.delete(f"/users/{user_id}")
    assert del_user_resp.status_code == 204
    print("Delete User OK")

def test_notify_arrival():
    # 1. Створюємо замовлення
    order_data = {
        "id": 8888,
        "client_name": "Іван Тест",
        "client_phone": "+380501234567",
        "client_address": "Вул. Тестова, 5"
    }
    client.post("/orders/", json=order_data)
    
    # 2. Переводимо замовлення у статус "В дорозі" (штучно або через assign_courier і оновлення)
    # Зручніше використати /assign, що ставитиме "Призначено кур'єра", цього достатньо
    assign_resp = client.post("/orders/8888/assign")
    assert assign_resp.status_code == 200
    
    # 3. Викликаємо notify-arrival
    notify_resp = client.post("/orders/8888/notify-arrival")
    assert notify_resp.status_code == 200
    
    data = notify_resp.json()
    assert data["order_status"] == "Кур'єр очікує"
    assert "Іван Тест" in data["message"]
    
    # 4. Виклик для замовлення зі статусом "Кур'єр очікує" (не в дорозі) має видати 400
    notify_err = client.post("/orders/8888/notify-arrival")
    assert notify_err.status_code == 400
    print("Notify Arrival OK")

    # Прибирання за собою
    client.delete("/orders/8888")

if __name__ == "__main__":
    test_health()
    test_sorting()
    test_user_creation()
    test_delete_endpoints()
    test_notify_arrival()
    print("All tests passed!")
