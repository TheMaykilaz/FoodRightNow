// app.js

const API_BASE = window.location.origin; // Dynamically use the same origin where the frontend is served
let currentPage = 1;
const limit = 10;
let currentFilter = '';

document.addEventListener('DOMContentLoaded', () => {
    loadOrders();

    document.getElementById('create-order-form').addEventListener('submit', handleCreateOrder);
    
    document.getElementById('status-filter').addEventListener('change', (e) => {
        currentFilter = e.target.value;
        currentPage = 1;
        loadOrders();
    });

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadOrders();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        currentPage++;
        loadOrders();
    });
});

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Add icon based on type
    const icon = type === 'success' ? '✅' : '❌';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    const removeToast = () => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    };

    setTimeout(removeToast, 4000);
    toast.onclick = removeToast;
}

// Грамотна обробка помилок (Error Handling)
async function handleResponse(response) {
    if (!response.ok) {
        let errorMsg = 'Сталася невідома помилка';
        try {
            const errorData = await response.json();
            // FastAPI validation errors (422) return an array of issues in `detail`
            if (Array.isArray(errorData.detail)) {
                errorMsg = errorData.detail.map(err => {
                    const loc = err.loc.join(' -> ');
                    return `${loc}: ${err.msg}`;
                }).join('<br>');
            } 
            // Other FastAPI exceptions HTTPExceptions usually return string in `detail`
            else if (errorData.detail) {
                errorMsg = errorData.detail;
            } 
            // Custom response formats might use `message`
            else if (errorData.message) {
                errorMsg = errorData.message;
            }
        } catch (e) {
            errorMsg = `Помилка сервера: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMsg);
    }
    
    if (response.status === 204) {
        return null; // HTTP_204_NO_CONTENT
    }
    
    return response.json();
}

async function loadOrders() {
    const tbody = document.getElementById('orders-tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light">Завантаження...</td></tr>';

    try {
        const skip = (currentPage - 1) * limit;
        let url = `${API_BASE}/orders/?skip=${skip}&limit=${limit}`;
        if (currentFilter) {
            url += `&status_filter=${encodeURIComponent(currentFilter)}`;
        }
        
        const response = await fetch(url);
        const data = await handleResponse(response);
        
        renderOrdersTable(data);
        
        // Оновлення стану кнопок пагінації
        document.getElementById('page-info').textContent = `Сторінка ${currentPage}`;
        document.getElementById('prev-page').disabled = currentPage === 1;
        // Якщо повернуто менше ніж ліміт, значить це остання сторінка
        document.getElementById('next-page').disabled = data.length < limit;

    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light" style="color:var(--error-color);">Не вдалося завантажити дані</td></tr>';
        showToast(error.message, 'error');
    }
}

function getStatusClass(status) {
    const map = {
        "Очікує оплати": "status-awaiting-payment",
        "Створено": "status-created",
        "Призначено кур'єра": "status-assigned",
        "В дорозі": "status-transit",
        "Кур'єр очікує": "status-waiting",
        "Доставлено": "status-delivered",
        "Скасовано": "status-cancelled"
    };
    return map[status] || "";
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('orders-tbody');
    tbody.innerHTML = '';
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light">Замовлень не знайдено</td></tr>';
        return;
    }

    orders.forEach(order => {
        const tr = document.createElement('tr');
        
        // Логіка кнопок дій, що залежить від статусу
        let actionsHtml = `<div style="display: flex; flex-direction: column; gap: 0.5rem;">`;
        if (order.status === 'Очікує оплати') {
            actionsHtml += `<button class="btn small primary full-width" style="background-color: #635bff;" onclick="payOrder(${order.id})">💳 Оплатити</button>`;
        } else if (order.status === 'Створено') {
            actionsHtml += `<button class="btn small primary full-width" onclick="assignCourier(${order.id})">Призначити кур'єра</button>`;
        } else if (order.status === 'В дорозі' || order.status === "Призначено кур'єра") {
            actionsHtml += `<button class="btn small secondary full-width" onclick="notifyArrival(${order.id})">Спов. про прибуття</button>`;
            actionsHtml += `<button class="btn small secondary full-width" onclick="trackOrder(${order.id})">📍 Відстежити</button>`;
        } else if (order.status === "Кур'єр очікує") {
            actionsHtml += `<button class="btn small" style="background-color: var(--success-color); color: white; width: 100%;" onclick="markDelivered(${order.id})">Доставлено</button>`;
            actionsHtml += `<button class="btn small secondary full-width" onclick="trackOrder(${order.id})">📍 Відстежити</button>`;
        } else if (order.status === 'Доставлено' || order.status === 'Скасовано') {
            actionsHtml += `<div class="text-center" style="font-size: 0.8rem; color: var(--success-color); font-weight: 500;">✓ Завершено</div>`;
        }
        
        actionsHtml += `<button class="btn small error" style="background-color: var(--error-color); color: white; width: 100%;" onclick="deleteOrder(${order.id})">🗑 Видалити</button>`;
        actionsHtml += `</div>`;
        
        const client_name = order.client_name || order.client_id || 'Невідомий';
        const client_phone = order.client_phone || 'Не вказано';
        const client_address = order.client_address || 'Не вказано';
        
        tr.innerHTML = `
            <td><strong>#${order.id}</strong></td>
            <td>${client_name}<br><small class="text-light">${client_phone}</small></td>
            <td>${client_address}</td>
            <td style="font-weight: 500;">₴${parseFloat(order.price || 0).toFixed(2)}</td>
            <td><span class="status-badge ${getStatusClass(order.status)}">${order.status}</span></td>
            <td>${actionsHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Подія створення замовлення
async function handleCreateOrder(e) {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Створення...';
    
    const id = parseInt(document.getElementById('order-id').value);
    const client_name = document.getElementById('client-name').value;
    const client_phone = document.getElementById('client-phone').value;
    const client_address = document.getElementById('client-address').value;
    const price = document.getElementById('price').value;

    const payload = {
        id,
        client_name,
        client_phone,
        client_address,
        price: parseFloat(price)
    };

    try {
        const response = await fetch(`${API_BASE}/orders/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        await handleResponse(response);
        
        showToast('Замовлення успішно створено!', 'success');
        document.getElementById('create-order-form').reset();
        
        // Скидаємо фільтр та йдемо на першу сторінку для відображення нового замовлення
        currentFilter = '';
        document.getElementById('status-filter').value = '';
        currentPage = 1;
        loadOrders();
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Створити Замовлення';
    }
}

// Призначити кур'єра
window.assignCourier = async function(orderId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/assign`, {
            method: 'POST'
        });
        await handleResponse(response);
        showToast(`Кур'єра успішно призначено для замовлення #${orderId}`, 'success');
        loadOrders();
    } catch (error) {
        showToast(error.message, 'error');
    }
};

// Сповістити клієнта
window.notifyArrival = async function(orderId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/notify-arrival`, {
            method: 'POST'
        });
        const data = await handleResponse(response);
        showToast(data.message || `Клієнт отримав сповіщення про замовлення #${orderId}`, 'success');
        loadOrders();
    } catch (error) {
        showToast(error.message, 'error');
    }
};

// Відмітити як доставлено
window.markDelivered = async function(orderId) {
    try {
        const statusEncoded = encodeURIComponent('Доставлено');
        const response = await fetch(`${API_BASE}/orders/${orderId}/status?new_status=${statusEncoded}`, {
            method: 'PATCH'
        });
        await handleResponse(response);
        showToast(`Замовлення #${orderId} успішно доставлено!`, 'success');
        loadOrders();
    } catch (error) {
        showToast(error.message, 'error');
    }
};

// Відстеження замовлення
window.trackOrder = async function(orderId) {
    try {
        const response = await fetch(`${API_BASE}/tracking/${orderId}`);
        const data = await handleResponse(response);
        
        const orderResponse = await fetch(`${API_BASE}/orders/${orderId}`);
        const orderData = await handleResponse(orderResponse);
        
        document.getElementById('track-order-id').textContent = `#${orderId}`;
        document.getElementById('track-location').textContent = data.current_location || 'Невідомо';
        document.getElementById('track-route').textContent = orderData.route || 'Маршрут відсутній';
        
        document.getElementById('tracking-modal').style.display = 'flex';
    } catch (error) {
        showToast(error.message, 'error');
    }
};

window.closeTrackingModal = function() {
    document.getElementById('tracking-modal').style.display = 'none';
};

// Видалити замовлення
window.deleteOrder = async function(orderId) {
    if (!confirm(`Ви впевнені, що хочете назавжди видалити замовлення #${orderId}?`)) return;
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}`, {
            method: 'DELETE'
        });
        await handleResponse(response);
        showToast(`Замовлення #${orderId} успішно видалено`, 'success');
        loadOrders();
    } catch (error) {
        showToast(error.message, 'error');
    }
};

window.payOrder = async function(orderId) {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Завантаження...';
    btn.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/create-checkout-session`, {
            method: 'POST'
        });
        const data = await handleResponse(response);
        if (data.checkout_url) {
            window.location.href = data.checkout_url;
        }
    } catch (error) {
        showToast(error.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};
