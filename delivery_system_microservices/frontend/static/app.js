// Microservice URLs
const SERVICES = {
    orders:   'http://localhost:8001',
    couriers: 'http://localhost:8002',
    tracking: 'http://localhost:8003',
    reports:  'http://localhost:8004'
};

let currentPage = 1;
const limit = 10;
let currentFilter = '';

// ======================== INIT ========================
document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Order form
    document.getElementById('create-order-form').addEventListener('submit', handleCreateOrder);

    // Filters & pagination
    document.getElementById('status-filter').addEventListener('change', (e) => {
        currentFilter = e.target.value;
        currentPage = 1;
        loadOrders();
    });
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) { currentPage--; loadOrders(); }
    });
    document.getElementById('next-page').addEventListener('click', () => {
        currentPage++;
        loadOrders();
    });

    // Set default daily date to today
    document.getElementById('daily-date').value = new Date().toISOString().split('T')[0];

    // Initial loads
    loadOrders();
    checkServicesHealth();
    setInterval(checkServicesHealth, 15000);
});

// ======================== TABS ========================
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Lazy-load data for each tab
    if (tabName === 'orders') loadOrders();
    if (tabName === 'couriers') loadCouriers();
    if (tabName === 'reports') { loadGeneralReport(); loadWeeklyReport(); }
}

// ======================== HEALTH ========================
async function checkServicesHealth() {
    const checks = [
        { id: 'status-orders',   url: SERVICES.orders },
        { id: 'status-couriers', url: SERVICES.couriers },
        { id: 'status-tracking', url: SERVICES.tracking },
        { id: 'status-reports',  url: SERVICES.reports },
    ];
    for (const svc of checks) {
        try {
            const r = await fetch(`${svc.url}/health`, { signal: AbortSignal.timeout(3000) });
            document.getElementById(svc.id).className = r.ok ? 'status-dot online' : 'status-dot offline';
        } catch {
            document.getElementById(svc.id).className = 'status-dot offline';
        }
    }
}

// ======================== TOAST ========================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
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

// ======================== ERROR HANDLING ========================
async function handleResponse(response) {
    if (!response.ok) {
        let errorMsg = 'Сталася невідома помилка';
        try {
            const errorData = await response.json();
            if (Array.isArray(errorData.detail)) {
                errorMsg = errorData.detail.map(err => `${err.loc.join(' -> ')}: ${err.msg}`).join('<br>');
            } else if (errorData.detail) {
                errorMsg = errorData.detail;
            } else if (errorData.message) {
                errorMsg = errorData.message;
            }
        } catch (e) {
            errorMsg = `Помилка сервера: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMsg);
    }
    if (response.status === 204) return null;
    return response.json();
}

// ======================== ORDERS (port 8001) ========================
async function loadOrders() {
    const tbody = document.getElementById('orders-tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light">Завантаження...</td></tr>';
    try {
        const skip = (currentPage - 1) * limit;
        let url = `${SERVICES.orders}/orders/?skip=${skip}&limit=${limit}`;
        if (currentFilter) url += `&status_filter=${encodeURIComponent(currentFilter)}`;
        const response = await fetch(url);
        const data = await handleResponse(response);
        renderOrdersTable(data);
        document.getElementById('page-info').textContent = `Сторінка ${currentPage}`;
        document.getElementById('prev-page').disabled = currentPage === 1;
        document.getElementById('next-page').disabled = data.length < limit;
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light" style="color:var(--error-color);">Не вдалося завантажити</td></tr>';
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

async function handleCreateOrder(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Створення...';

    const payload = {
        id: parseInt(document.getElementById('order-id').value),
        client_name: document.getElementById('client-name').value,
        client_phone: document.getElementById('client-phone').value,
        client_address: document.getElementById('client-address').value,
        price: parseFloat(document.getElementById('price').value)
    };

    try {
        const response = await fetch(`${SERVICES.orders}/orders/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        await handleResponse(response);
        showToast('Замовлення успішно створено!', 'success');
        document.getElementById('create-order-form').reset();
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

window.assignCourier = async function(orderId) {
    try {
        const response = await fetch(`${SERVICES.orders}/orders/${orderId}/assign`, { method: 'POST' });
        await handleResponse(response);
        showToast(`Кур'єра успішно призначено для замовлення #${orderId}`, 'success');
        loadOrders();
    } catch (error) { showToast(error.message, 'error'); }
};

window.notifyArrival = async function(orderId) {
    try {
        const response = await fetch(`${SERVICES.orders}/orders/${orderId}/notify-arrival`, { method: 'POST' });
        const data = await handleResponse(response);
        showToast(data.message || `Клієнт отримав сповіщення`, 'success');
        loadOrders();
    } catch (error) { showToast(error.message, 'error'); }
};

window.markDelivered = async function(orderId) {
    try {
        const statusEncoded = encodeURIComponent('Доставлено');
        const response = await fetch(`${SERVICES.orders}/orders/${orderId}/status?new_status=${statusEncoded}`, { method: 'PATCH' });
        await handleResponse(response);
        showToast(`Замовлення #${orderId} успішно доставлено!`, 'success');
        loadOrders();
    } catch (error) { showToast(error.message, 'error'); }
};

window.deleteOrder = async function(orderId) {
    if (!confirm(`Ви впевнені, що хочете видалити замовлення #${orderId}?`)) return;
    try {
        const response = await fetch(`${SERVICES.orders}/orders/${orderId}`, { method: 'DELETE' });
        await handleResponse(response);
        showToast(`Замовлення #${orderId} видалено`, 'success');
        loadOrders();
    } catch (error) { showToast(error.message, 'error'); }
};

window.payOrder = async function(orderId) {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Завантаження...';
    btn.disabled = true;
    try {
        const response = await fetch(`${SERVICES.orders}/orders/${orderId}/create-checkout-session`, { method: 'POST' });
        const data = await handleResponse(response);
        if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (error) {
        showToast(error.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

// Track from orders table (modal)
window.trackOrder = async function(orderId) {
    try {
        const response = await fetch(`${SERVICES.tracking}/tracking/${orderId}`);
        const data = await handleResponse(response);
        document.getElementById('track-order-id').textContent = `#${orderId}`;
        document.getElementById('track-location').textContent = data.current_location || 'Невідомо';
        document.getElementById('track-route').textContent = data.route || 'Маршрут відсутній';
        document.getElementById('tracking-modal').style.display = 'flex';
    } catch (error) { showToast(error.message, 'error'); }
};

window.closeTrackingModal = function() {
    document.getElementById('tracking-modal').style.display = 'none';
};

// ======================== COURIERS (port 8002) ========================
window.loadCouriers = async function() {
    const tbody = document.getElementById('couriers-tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light">Завантаження...</td></tr>';
    try {
        const response = await fetch(`${SERVICES.couriers}/couriers/`);
        const couriers = await handleResponse(response);
        tbody.innerHTML = '';
        if (couriers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light">Кур\u0027єрів не знайдено</td></tr>';
            return;
        }
        couriers.forEach(c => {
            const tr = document.createElement('tr');
            const availClass = c.is_available ? 'status-delivered' : 'status-transit';
            const availText = c.is_available ? 'Вільний' : 'Зайнятий';
            tr.innerHTML = `
                <td><strong>#${c.id}</strong></td>
                <td>${c.name}</td>
                <td><span class="status-badge ${availClass}">${availText}</span></td>
                <td>${c.current_location || '—'}</td>
                <td>${c.current_order_id ? '#' + c.current_order_id : '—'}</td>
                <td>${c.destination || '—'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-light" style="color:var(--error-color);">Помилка завантаження</td></tr>';
        showToast(error.message, 'error');
    }
};

// ======================== TRACKING (port 8003) ========================
window.trackOrderById = async function() {
    const orderId = document.getElementById('track-input-id').value;
    if (!orderId) { showToast('Введіть ID замовлення', 'error'); return; }
    try {
        const response = await fetch(`${SERVICES.tracking}/tracking/${orderId}`);
        const data = await handleResponse(response);
        document.getElementById('tr-order-id').textContent = `#${data.order_id}`;
        document.getElementById('tr-status').innerHTML = `<span class="status-badge ${getStatusClass(data.status)}">${data.status}</span>`;
        document.getElementById('tr-courier').textContent = data.courier_name || 'Не призначено';
        document.getElementById('tr-location').textContent = data.current_location || 'Невідомо';
        document.getElementById('tr-route').textContent = data.route || 'Маршрут відсутній';
        document.getElementById('tr-address').textContent = data.client_address || '—';
        document.getElementById('tracking-result').style.display = 'block';
    } catch (error) {
        document.getElementById('tracking-result').style.display = 'none';
        showToast(error.message, 'error');
    }
};

// ======================== REPORTS (port 8004) ========================
async function loadGeneralReport() {
    try {
        const response = await fetch(`${SERVICES.reports}/reports/deliveries`);
        const data = await handleResponse(response);
        document.getElementById('rpt-total').textContent = data.total_orders;
        document.getElementById('rpt-delivered').textContent = data.delivered_orders;
        document.getElementById('rpt-cancelled').textContent = data.cancelled_orders;
        document.getElementById('rpt-pending').textContent = data.pending_orders;
        document.getElementById('rpt-avg-price').textContent = data.average_order_price.toFixed(2);
    } catch (error) { showToast('Не вдалося завантажити загальний звіт', 'error'); }
}

async function loadWeeklyReport() {
    try {
        const response = await fetch(`${SERVICES.reports}/reports/weekly`);
        const data = await handleResponse(response);
        document.getElementById('weekly-period').textContent = `Період: ${data.period}`;
        document.getElementById('wrpt-total').textContent = data.total_orders;
        document.getElementById('wrpt-delivered').textContent = data.delivered_orders;
        document.getElementById('wrpt-cancelled').textContent = data.cancelled_orders;
        document.getElementById('wrpt-revenue').textContent = data.total_revenue.toFixed(2);
        document.getElementById('wrpt-couriers').textContent = data.active_couriers_count;
    } catch (error) { showToast('Не вдалося завантажити тижневий звіт', 'error'); }
}

window.loadDailyReport = async function() {
    const date = document.getElementById('daily-date').value;
    if (!date) { showToast('Виберіть дату', 'error'); return; }
    try {
        const response = await fetch(`${SERVICES.reports}/reports/daily?date=${date}`);
        const data = await handleResponse(response);
        document.getElementById('drpt-total').textContent = data.total_orders;
        document.getElementById('drpt-delivered').textContent = data.delivered_orders;
        document.getElementById('drpt-cancelled').textContent = data.cancelled_orders;
        document.getElementById('drpt-revenue').textContent = data.total_revenue.toFixed(2);
        document.getElementById('drpt-avg').textContent = data.average_order_price.toFixed(2);
    } catch (error) { showToast(error.message, 'error'); }
};
