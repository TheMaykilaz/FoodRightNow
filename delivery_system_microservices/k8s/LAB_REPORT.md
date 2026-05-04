# Лабораторна робота: Розгортання мікросервісної системи в Kubernetes

---

## Мета роботи

Розгорнути мікросервісну систему доставки у локальному Kubernetes-кластері (Minikube), налаштувати масштабування, перевірити доступність сервісів, міжсервісну комунікацію, підключення до Redis, поведінку при видаленні Pod та виконати rolling update.

---

## 1. Постановка задачі

### 1.1 Розгорнуті сервіси

| Сервіс | Порт | Реплік | Призначення |
|--------|------|--------|-------------|
| order-service | 8001 | 2 | Управління замовленнями, користувачами, призначення кур'єрів, оплата |
| courier-service | 8002 | 1 | Управління кур'єрами, відстеження доступності |
| tracking-service | 8003 | 1 | Відстеження доставки в реальному часі |
| reporting-service | 8004 | 1 | Звіти про доставку, денна/тижнева статистика |
| frontend | 8000 | 1 | Веб-інтерфейс (HTML/CSS/JS) |
| redis | 6379 | 1 | Кешування (внутрішній ClusterIP) |

### 1.2 Створені Deployment

```
$ kubectl get deployments -n delivery-system

NAME                READY   UP-TO-DATE   AVAILABLE
order-service       2/2     2            2
courier-service     1/1     1            1
tracking-service    1/1     1            1
reporting-service   1/1     1            1
frontend            1/1     1            1
redis               1/1     1            1
```

Всього: **6 Deployment**, **7 Pod** (order-service має 2 репліки).

### 1.3 Реалізоване масштабування

| Параметр | Значення |
|----------|----------|
| Початкова кількість реплік (order-service) | 2 |
| Масштабовано до | 4 реплік |
| Стратегія оновлення | RollingUpdate |
| maxSurge | 1 (дозволити 1 додатковий Pod під час оновлення) |
| maxUnavailable | 0 (ніколи не зменшувати нижче бажаної кількості) |
| Команда масштабування | `kubectl scale deployment order-service --replicas=4` |

---

## 2. Проектування

### 2.1 Архітектура кластера

```
┌─────────────────────────────────────────────────────────────────────┐
│                    КЛАСТЕР MINIKUBE (1 вузол)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Namespace: delivery-system                    │   │
│  │                                                              │   │
│  │  ┌────────────────┐          ┌────────────────────────┐     │   │
│  │  │   ConfigMap     │          │   PersistentVolume      │     │   │
│  │  │  (змінні сер.)  │          │   (SQLite БД, 100Mi)    │     │   │
│  │  └────────────────┘          └────────────────────────┘     │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  order-service (Deployment, 2 репліки)                │   │   │
│  │  │  ┌─────────┐  ┌─────────┐                            │   │   │
│  │  │  │  Pod 1   │  │  Pod 2   │  ← NodePort :30001       │   │   │
│  │  │  └─────────┘  └─────────┘                            │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │   │
│  │  │courier-service│ │tracking-svc  │ │reporting-svc │        │   │
│  │  │ (1 pod)       │ │ (1 pod)      │ │ (1 pod)      │        │   │
│  │  │ NP:30002      │ │ NP:30003     │ │ NP:30004     │        │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────────────────────────┐     │   │
│  │  │   frontend    │ │   redis (ClusterIP, внутрішній)   │     │   │
│  │  │ (1 pod)       │ │   (1 pod, порт 6379)             │     │   │
│  │  │ NP:30000      │ └──────────────────────────────────┘     │   │
│  │  └──────────────┘                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         ▲
         │ kubectl port-forward (localhost:8000-8004)
         │
    ┌────────────┐
    │   Клієнт    │ (Браузер / Postman)
    └────────────┘
```

### 2.2 Взаємодія компонентів

```
Клієнт (Postman/Браузер)
    │
    ├── GET/POST ──► order-service ──► Redis (перевірка кешу)
    │                     │
    │                     ├── HTTP ──► courier-service (призначення кур'єра)
    │                     │                  │
    │                     │                  └── SQLite БД (читання/запис)
    │                     │
    │                     └── SQLite БД (замовлення, користувачі)
    │
    ├── GET ──► tracking-service ──► Redis ──► SQLite БД
    │
    ├── GET ──► reporting-service ──► Redis ──► SQLite БД
    │
    └── GET ──► frontend (статичні HTML/JS/CSS файли)
```

**Міжсервісна комунікація:**
- order-service → courier-service: HTTP REST через K8s DNS (`http://courier-service:8002`)
- Усі сервіси → Redis: TCP через K8s DNS (`redis://redis-service:6379`)
- Усі сервіси → SQLite: спільний PersistentVolume, змонтований у `/data/delivery.db`

### 2.3 Структура YAML-файлів

```
k8s/
├── namespace.yaml                    # Простір імен: delivery-system
├── configmap.yaml                    # Спільні змінні середовища
├── pv-database.yaml                  # PersistentVolume + PVC для SQLite
├── redis-deployment.yaml             # Redis Deployment (1 репліка)
├── redis-service.yaml                # Redis ClusterIP Service
├── seed-job.yaml                     # Одноразовий Job для заповнення БД
├── order-service-deployment.yaml     # Order Deployment (2 репліки)
├── order-service-svc.yaml            # Order NodePort Service
├── courier-service-deployment.yaml   # Courier Deployment (1 репліка)
├── courier-service-svc.yaml          # Courier NodePort Service
├── tracking-service-deployment.yaml  # Tracking Deployment (1 репліка)
├── tracking-service-svc.yaml         # Tracking NodePort Service
├── reporting-service-deployment.yaml # Reporting Deployment (1 репліка)
├── reporting-service-svc.yaml        # Reporting NodePort Service
├── frontend-deployment.yaml          # Frontend Deployment (1 репліка)
├── frontend-svc.yaml                 # Frontend NodePort Service
├── deploy.ps1                        # Скрипт автоматичного розгортання
├── demo.ps1                          # Скрипт демонстрації
└── REPORT.md                         # Звіт
```

---

## 3. Реалізація

### 3.1 Deployment YAML (приклад: order-service)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: delivery-system
spec:
  replicas: 2                          # Висока доступність
  selector:
    matchLabels:
      app: order-service
  strategy:
    type: RollingUpdate                # Оновлення без простою
    rollingUpdate:
      maxSurge: 1                      # Максимум 1 додатковий Pod
      maxUnavailable: 0                # Жоден Pod не може бути недоступним
  template:
    metadata:
      labels:
        app: order-service
        version: v1
    spec:
      containers:
        - name: order-service
          image: order-service:latest
          imagePullPolicy: Never       # Використовувати локальні образи Minikube
          ports:
            - containerPort: 8001
          envFrom:
            - configMapRef:
                name: delivery-config  # Завантажити змінні з ConfigMap
          resources:
            requests:                  # Мінімальні гарантовані ресурси
              memory: "128Mi"
              cpu: "100m"
            limits:                    # Максимальні ресурси
              memory: "256Mi"
              cpu: "250m"
          readinessProbe:              # Перевірка готовності приймати трафік
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:               # Перевірка працездатності (перезапуск)
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 15
            periodSeconds: 10
          volumeMounts:
            - name: db-storage
              mountPath: /data
      volumes:
        - name: db-storage
          persistentVolumeClaim:
            claimName: delivery-db-pvc
```

### 3.2 Service YAML (приклад: order-service)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: delivery-system
spec:
  type: NodePort                      # Доступний ззовні через NodePort
  selector:
    app: order-service                # Маршрутизація до всіх Pod з цим label
  ports:
    - port: 8001                      # Внутрішній порт кластера
      targetPort: 8001                # Порт контейнера
      nodePort: 30001                 # Зовнішній порт доступу
```

**Використані типи Service:**
- `NodePort` — order, courier, tracking, reporting, frontend (зовнішній доступ)
- `ClusterIP` — redis (тільки внутрішній доступ)

### 3.3 Команди kubectl

```powershell
# --- Розгортання ---
kubectl apply -f namespace.yaml           # Створити простір імен
kubectl apply -f configmap.yaml           # Створити конфігурацію
kubectl apply -f pv-database.yaml         # Створити том для БД
kubectl apply -f redis-deployment.yaml    # Розгорнути Redis
kubectl apply -f redis-service.yaml       # Створити сервіс Redis
kubectl apply -f seed-job.yaml            # Запустити заповнення БД
kubectl apply -f order-service-deployment.yaml  # Розгорнути order-service
kubectl apply -f order-service-svc.yaml         # Створити сервіс

# --- Моніторинг ---
kubectl get pods -n delivery-system -o wide          # Список Pod
kubectl get services -n delivery-system              # Список сервісів
kubectl get deployments -n delivery-system           # Список Deployment
kubectl logs deployment/order-service -n delivery-system  # Логи
kubectl describe pod <pod-name> -n delivery-system   # Деталі Pod

# --- Масштабування ---
kubectl scale deployment order-service -n delivery-system --replicas=4

# --- Rolling Update ---
kubectl set image deployment/order-service -n delivery-system \
  order-service=order-service:v2
kubectl rollout status deployment/order-service -n delivery-system
kubectl rollout history deployment/order-service -n delivery-system
kubectl rollout undo deployment/order-service -n delivery-system  # Відкат

# --- Видалення Pod (тест самовідновлення) ---
kubectl delete pod <pod-name> -n delivery-system

# --- Доступ до сервісів ---
kubectl port-forward svc/order-service 8001:8001 -n delivery-system

# --- Очищення ---
kubectl delete namespace delivery-system
minikube stop
```

### 3.4 Rolling Update (поетапне оновлення)

Процес оновлення з нульовим простоєм:

```
Стан 1 (до):     [Pod-v1-A] [Pod-v1-B]              (2/2 готові)
                       ↓
Крок 1: Новий:    [Pod-v1-A] [Pod-v1-B] [Pod-v2-C]  (maxSurge=1)
                       ↓
Крок 2: v2 готовий:[Pod-v1-A] [Pod-v1-B] [Pod-v2-C]  (3/3 готові)
                       ↓
Крок 3: Видалити:             [Pod-v1-B] [Pod-v2-C]  (2/2 готові)
                       ↓
Крок 4: Новий:               [Pod-v1-B] [Pod-v2-C] [Pod-v2-D]
                       ↓
Крок 5: Видалити:                        [Pod-v2-C] [Pod-v2-D]
                       ↓
Стан 2 (після):   [Pod-v2-C] [Pod-v2-D]             (2/2, без простою)
```

Виконані команди:
```powershell
# Запуск rolling update (зміна версії label)
kubectl patch deployment order-service -n delivery-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"version":"v2"}}}}}'

# Моніторинг процесу
kubectl rollout status deployment/order-service -n delivery-system
# Вивід: deployment "order-service" successfully rolled out

# Перевірка результату
kubectl get pods -n delivery-system -l app=order-service --show-labels
# Всі Pod мають version=v2
```

---

## 4. Тестування

### 4.1 Перевірка доступності сервісів

**Результат:** Всі сервіси відповіли успішно.
```
[STEP 1] Verifying service availability...
  OK  Order Service: ok
  OK  Courier Service: ok
  OK  Tracking Service: ok
  OK  Reporting Service: ok
```

**Метод:** HTTP GET на ендпоінт `/health` кожного сервісу через port-forward.

**Перевірка міжсервісної комунікації:**
```
  OK  Order #9000 created
  OK  Courier #1 assigned, route: Маршрут від Центральний склад до Kubernetes Street 1
  OK  Status: В дорозі, Location: Центральний склад
```

Це підтверджує: order-service → courier-service (призначення кур'єра) та tracking-service (відстеження) працюють коректно через K8s DNS.

**Перевірка підключення до Redis:**
```
  Request 1 (cold): X-Cache: MISS   ← Дані з БД, записано в кеш
  Request 2 (warm): X-Cache: HIT    ← Дані з Redis кешу
  Redis KEYS: cache:orders:list:limit=5:skip=0
```

### 4.2 Масштабування

**До масштабування (2 репліки):**
```
NAME                             READY   STATUS    AGE
order-service-544cd7f5cd-2mzg9   1/1     Running   17m
order-service-544cd7f5cd-4mxh8   1/1     Running   17m
```

**Команда:** `kubectl scale deployment order-service -n delivery-system --replicas=4`

**Після масштабування (4 репліки):**
```
NAME                             READY   STATUS    AGE
order-service-544cd7f5cd-2mzg9   1/1     Running   18m
order-service-544cd7f5cd-4mxh8   1/1     Running   18m
order-service-544cd7f5cd-fwcsq   1/1     Running   13s   ← НОВИЙ
order-service-544cd7f5cd-jcl4s   1/1     Running   13s   ← НОВИЙ
```

**Балансування навантаження підтверджено:**
```
Endpoints: 10.244.0.11:8001, 10.244.0.12:8001, 10.244.0.5:8001 + 1 more...
```
Всі 4 IP-адреси Pod зареєстровані як endpoints — K8s розподіляє трафік через kube-proxy.

### 4.3 Поведінка при зупинці Pod

**Видалено Pod:** `order-service-544cd7f5cd-2mzg9`

**Результат:** Deployment controller негайно створив заміну:
```
NAME                             READY   STATUS    AGE
order-service-544cd7f5cd-4mxh8   1/1     Running   20m
order-service-544cd7f5cd-fwcsq   1/1     Running   3m
order-service-544cd7f5cd-jcl4s   1/1     Running   3m
order-service-544cd7f5cd-xk9p2   1/1     Running   5s    ← ЗАМІНА
```

**Сервіс залишився доступним** — інші 3 Pod обробляли запити, поки новий Pod запускався. Нульовий простій.

---

## 5. Аналіз

### 5.1 Порівняння з Docker Compose

| Характеристика | Docker Compose | Kubernetes |
|----------------|---------------|------------|
| Область застосування | Одна машина | Багатовузловий кластер |
| Конфігурація | Один `docker-compose.yml` | Окремі YAML-маніфести (розділення відповідальності) |
| Масштабування | `--scale` (ручне, без балансування) | `replicas: N` з вбудованим балансуванням |
| Самовідновлення | `restart: always` (базове) | Deployment controller + проби (інтелектуальне) |
| Оновлення | Зупинка → Перебудова → Запуск (простій) | Rolling update (без простою) |
| Відкат | Не підтримується | `kubectl rollout undo` (миттєвий) |
| Виявлення сервісів | DNS за іменем контейнера | ClusterIP + CoreDNS (`svc.cluster.local`) |
| Балансування навантаження | Відсутнє (один контейнер) | kube-proxy (iptables/IPVS) |
| Контроль ресурсів | Опціональний `mem_limit` | Примусові requests/limits з QoS |
| Перевірка здоров'я | `healthcheck` (інформаційна) | readiness (трафік) + liveness (перезапуск) |
| Сховище | Docker volumes (локальне) | PV/PVC (локальне, NFS, хмарне) |
| Секрети | `.env` файли (відкритий текст) | K8s Secrets (base64, шифрування) |
| Мережа | Bridge network | Pod network (CNI) + Service network + Ingress |
| CI/CD інтеграція | Обмежена | Нативна (ArgoCD, Flux, Helm) |
| Продакшн | Тільки розробка/тестування | Промислового рівня |

### 5.2 Переваги оркестрації

1. **Висока доступність** — Множинні репліки + автоматичне відновлення після збоїв. Продемонстровано: Pod видалено, сервіс продовжив працювати без простою.

2. **Горизонтальне масштабування** — Масштабування з 2 до 4 реплік за секунди. У продакшні Horizontal Pod Autoscaler (HPA) може автоматично масштабувати на основі CPU/пам'яті.

3. **Оновлення без простою** — Rolling update поступово замінює Pod. `maxSurge: 1, maxUnavailable: 0` гарантує, що потужність сервісу ніколи не падає нижче бажаного стану.

4. **Самовідновлення** — Deployment controller постійно узгоджує фактичний стан з бажаним. Збійні Pod автоматично замінюються.

5. **Виявлення сервісів та балансування** — Сервіси знаходять один одного за DNS-іменем (`courier-service:8002`). kube-proxy рівномірно розподіляє трафік між усіма здоровими Pod.

6. **Контроль ресурсів** — CPU/memory requests гарантують мінімальні ресурси; limits запобігають впливу одного контейнера на інші.

7. **Декларативна інфраструктура як код** — Вся система описана у версійованих YAML-файлах. `kubectl apply` приводить кластер до бажаного стану ідемпотентно.

8. **Можливість відкату** — Кожна зміна Deployment записується. Одна команда повертає до будь-якої попередньої версії.

### 5.3 Доцільність використання

| Сценарій | Рекомендація |
|----------|-------------|
| Локальна розробка | Docker Compose (простіше, швидший запуск) |
| Staging/QA команди | Kubernetes (спільний кластер, namespaces на команду) |
| Продакшн (малий масштаб) | Managed K8s (GKE, EKS, AKS) |
| Продакшн (великий масштаб) | Kubernetes — необхідний для масштабування |
| CI/CD конвеєри | Kubernetes — GitOps з ArgoCD/Flux |
| Мікросервіси (>3 сервісів) | Kubernetes — service mesh, моніторинг |
| Моноліт | Docker Compose достатньо |

**Для нашої системи доставки:**
- 5 мікросервісів + Redis + спільна БД = **Kubernetes виправданий**
- Міжсервісна комунікація, кешування, масштабування = оркестрація дає чіткі переваги
- Продакшн-розгортання використовувало б:
  - PostgreSQL замість SQLite (Cloud SQL / RDS)
  - Redis Cluster (Elasticache / Memorystore)
  - Ingress controller замість NodePort
  - HPA для автомасштабування
  - Helm charts для шаблонізації

---

## 6. Висновки

Систему доставки успішно розгорнуто у локальному Kubernetes-кластері (Minikube):

- **6 Deployment** (5 сервісів + Redis)
- **7 працюючих Pod** (order-service з 2 репліками)
- Повна міжсервісна комунікація через K8s DNS
- Redis кешування працює (X-Cache: HIT/MISS перевірено)
- Масштабування протестовано: 2 → 4 репліки з балансуванням навантаження
- Самовідновлення підтверджено: видалення Pod → автоматична заміна
- Rolling update виконано: v1 → v2 без простою

Kubernetes забезпечує значні переваги над Docker Compose для мікросервісних архітектур, особливо у доступності, масштабованості та операційній надійності. Для систем з більш ніж 3 сервісами та вимогами до високої доступності використання Kubernetes є доцільним та рекомендованим.
