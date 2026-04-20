start "" cmd /k "title CourierService && cd courier_service && python main.py"
start "" cmd /k "title OrderService && cd order_service && python main.py"
echo "Started both microservices."
