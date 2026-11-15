# 🍔 CampusBite – Restaurant Ordering & Delivery Platform

CampusBite is a full-stack food ordering and delivery app for a college campus. **Customers** browse restaurants, order food, track deliveries, leave reviews, request refunds and get AI insights about their orders. **Restaurant owners** manage their menus, orders, delivery assignments and refunds. **Delivery partners** handle the orders assigned to them.

| Layer | Technology |
|---|---|
| Frontend | React 18 (Vite), React Router DOM 6, React Hooks + Context, Axios, plain responsive CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 ORM, JWT (PyJWT), bcrypt |
| Database | PostgreSQL 16 (Docker). SQLite fallback for quick local runs and tests |
| AI | OpenAI API (Chat Completions, default model `gpt-4o-mini`) |
| DevOps | Docker, Docker Compose, Git/GitHub |

---

## ✨ Features

### Customer
- Register / log in (JWT stored in `localStorage`, sent as `Authorization: Bearer …`)
- Browse restaurants (search, cuisine filter, ratings, pagination)
- View menus and **search/filter dishes by name and price range**, by category, and sort by price. There is also a dish search across all restaurants
- Cart: add, update quantity, remove, clear (one restaurant per cart, saved in the browser)
- Checkout with a **dummy payment** (card/UPI/wallet). The order becomes `mock_paid` and a payment-ledger entry is written
- Order history with **status + date filters** and pagination; live order tracking (progress tracker + timeline)
- Cancel an order while it is `PLACED` (the dummy payment is refunded automatically)
- Rate & review delivered orders (one review per order)
- Request a return/refund after delivery, with a reason (one request per order)
- **AI Order Insights**: summaries and free-form questions about *their own* orders, plus statistics computed locally

### Restaurant owner
- Dashboard with statistics: orders today, active orders, revenue, average order value, rating, a 7-day chart, top dishes, orders by status
- Menu management: add / edit / delete dishes, toggle available/unavailable
- Order management: filter by status and date, accept → preparing → ready, reject, **assign a delivery partner** to READY orders
- Approve or reject return/refund requests (approval sets `payment_status=refunded`, adds a refund ledger entry and moves the order to `REFUNDED`)
- **Reminders** for orders left in `PLACED`/`ACCEPTED` for more than 15 minutes (a background task creates them)
- Open/close the restaurant

### Delivery partner
- Sees **only orders assigned to them**, including the customer's name, phone and address
- `ASSIGNED → OUT_FOR_DELIVERY → DELIVERED`
- Active deliveries and delivery history, with filters, pagination and simple stats

### Platform
- Role-based access control on **every backend endpoint**. Frontend route guards are extra, not a replacement
- A central order **state machine**. Invalid transitions return `409 Conflict`
- Middleware that logs method, path, status and duration for each request, and adds `X-Process-Time` / `X-Request-ID` headers
- A background scheduler (asyncio) plus an on-demand FastAPI `BackgroundTasks` scan for reminders
- Pagination on every list endpoint
- Responsive UI (desktop and mobile) with light/dark mode

---

## 📁 Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, middleware, lifespan (DB init, seed, scheduler)
│   │   ├── config.py            # Settings from environment variables
│   │   ├── database.py          # Engine, session, Base, DB wait/init
│   │   ├── models.py            # SQLAlchemy models (all tables)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── security.py          # bcrypt, JWT, role dependencies
│   │   ├── middleware.py        # Request logging + timing
│   │   ├── utils.py             # Pagination + order filters
│   │   ├── seed.py              # Demo data
│   │   ├── routers/             # auth, restaurants, orders, owner, delivery, ai
│   │   └── services/            # order_workflow (state machine, payments), reminders, ai_insights
│   ├── tests/                   # pytest end-to-end API tests
│   ├── Dockerfile
│   ├── requirements.txt / requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 # axios client (JWT interceptor) + service functions
│   │   ├── context/             # AuthContext, CartContext
│   │   ├── hooks/               # useApi, useDebounce
│   │   ├── components/          # Navbar, ProtectedRoute, OrderCard, OrderActions, Pagination, Modal, …
│   │   └── pages/               # Login, Register, Restaurants, RestaurantMenu, Cart, OrderDetail,
│   │                            # customer/, owner/, delivery/
│   └── .env.example
├── docker-compose.yml           # PostgreSQL + FastAPI backend
├── .env.example                 # Variables for docker compose
└── README.md
```

---

## 🚀 Getting started

### Prerequisites
- Docker Desktop (or Docker Engine + the Compose plugin)
- Node.js 18+ and npm
- *(optional, for running the backend without Docker)* Python 3.12+

### 1. Run the backend with Docker Compose

```bash
# from the project root
cp .env.example .env
```

Edit `.env` and set at least:

| Variable | How to fill it |
|---|---|
| `POSTGRES_PASSWORD` | any strong password |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `OPENAI_API_KEY` | your OpenAI key (optional: AI insights return 503 without it) |

```bash
docker compose up --build        # add -d to run in the background
```

- API: http://localhost:8000
- Interactive API docs (Swagger): http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/health

When the backend starts, it waits for PostgreSQL, creates the tables, and (with `SEED_DEMO_DATA=true`) loads demo data.

Useful commands:
```bash
docker compose logs -f backend   # request logs (method, path, status, duration)
docker compose down              # stop
docker compose down -v           # stop AND delete the database volume (fresh start)
```

### 2. Run the frontend

```bash
cd frontend
cp .env.example .env             # VITE_API_BASE_URL=http://localhost:8000/api
npm install
npm run dev                      # http://localhost:5173
```

Production build: `npm run build` (output in `frontend/dist/`).

### 3. Demo accounts

All demo accounts use the password **`Password@123`**. The login page has one-click buttons to fill them in.

| Role | Email | Notes |
|---|---|---|
| Customer | `customer@campusbite.dev` | Has order history (delivered, in progress, cancelled, a pending return) |
| Customer | `customer2@campusbite.dev` | |
| Restaurant owner | `owner@campusbite.dev` | Campus Grill: active orders and 2 stale-order reminders |
| Restaurant owner | `owner2@campusbite.dev` | Green Bowl Café: one pending return request |
| Restaurant owner | `owner3@campusbite.dev` | Noodle Nook |
| Delivery partner | `rider@campusbite.dev` | Has an assigned order |
| Delivery partner | `rider2@campusbite.dev` | |

You can also register new accounts for any role. Registering as a restaurant owner also creates the restaurant.

### (Optional) Run the backend without Docker

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # uses SQLite by default; set JWT_SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

### Run the tests

```bash
cd backend
pytest -q
```

The 16 end-to-end tests run against a temporary SQLite database. They cover registration and login, RBAC, every order status transition including invalid ones, cancellation, dummy payment and refunds, reviews, returns (approve and reject, no duplicates), data isolation between users, pagination and filters, stats, background reminders, the AI endpoint (no key → 503, mocked OpenAI, context limited to the customer's own orders) and the middleware headers.

---

## 🔐 Environment variables

Root `.env` (read by `docker compose`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `POSTGRES_USER` | | `campusbite` | DB user |
| `POSTGRES_PASSWORD` | ✅ | – | DB password |
| `POSTGRES_DB` | | `campusbite` | DB name |
| `JWT_SECRET_KEY` | ✅ | – | Secret used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `120` | Token lifetime |
| `CORS_ORIGINS` | | `http://localhost:5173,…` | Comma-separated allowed frontend origins |
| `OPENAI_API_KEY` | | – | Enables AI insights |
| `OPENAI_MODEL` | | `gpt-4o-mini` | OpenAI model |
| `AI_RATE_LIMIT_PER_MINUTE` | | `5` | AI requests allowed per customer per minute |
| `REMINDER_THRESHOLD_MINUTES` | | `15` | When an order counts as stale |
| `REMINDER_SCAN_INTERVAL_SECONDS` | | `60` | How often the background scan runs |
| `SEED_DEMO_DATA` | | `true` | Load demo data into an empty DB |
| `BACKEND_PORT` / `POSTGRES_PORT` | | `8000` / `5432` | Host ports |

The backend also reads `DATABASE_URL` (Compose builds it from the Postgres variables), `DELIVERY_FEE` (default 30), `ENABLE_REMINDER_SCHEDULER` and `LOG_LEVEL`. See `backend/.env.example`.

Frontend `frontend/.env`: `VITE_API_BASE_URL` (default `http://localhost:8000/api`).

> **Secrets are never committed.** `.env` files are in `.gitignore` and `.dockerignore`. Only the `.env.example` templates, which contain no values, are in the repository. Secrets reach the container as runtime environment variables and are never copied into the image.

---

## 🗄️ Database

Tables are created automatically when the app starts (`Base.metadata.create_all`). There are no manual steps: Docker Compose starts PostgreSQL with a persistent volume (`pgdata`). To reset the data, run `docker compose down -v`. To reload demo data into an empty database manually, run `python -m app.seed`.

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | All accounts; `role` ∈ customer / restaurant_owner / delivery_partner | – |
| `restaurants` | Restaurant profile | `owner_id → users` |
| `menu_items` | Dishes (price, category, veg, availability) | `restaurant_id → restaurants` (1-N) |
| `orders` | Order header: status, payment & return status, totals, address | `customer_id → users`, `restaurant_id → restaurants`, `delivery_partner_id → users` (nullable) |
| `order_items` | Order lines (name and price copied at order time) | `order_id → orders` (1-N), `menu_item_id → menu_items` (SET NULL) |
| `reviews` | Rating 1–5 + comment | `order_id → orders` **unique** (one review per order) |
| `payment_ledger` | Dummy payment and refund records | `order_id → orders` (1-N) |
| `admin_reminder_logs` | Stale-order reminders | `order_id → orders`, `restaurant_id → restaurants` |
| `order_status_history` | Audit trail of every status change | `order_id → orders` |

Money is stored as `NUMERIC(10,2)`. CHECK constraints enforce `price >= 0`, `quantity > 0` and `rating BETWEEN 1 AND 5`. Timestamps are stored in UTC.

---

## 🔄 Order lifecycle

```
PLACED ──► ACCEPTED ──► PREPARING ──► READY ──► ASSIGNED ──► OUT_FOR_DELIVERY ──► DELIVERED ──► REFUNDED
  │  (owner)       (owner)       (owner)   (owner assigns)    (delivery)          (delivery)   (owner approves return)
  └──► CANCELLED  (customer cancels / owner rejects – only from PLACED; payment auto-refunded)
```

All transitions go through `services/order_workflow.py`, which checks both the **source → target** pair and the **role** of the user making the change.
- A transition that isn't in the table (for example, `PLACED → READY` or cancelling a delivered order) returns `409 Conflict`.
- A valid transition attempted by the wrong role returns `403`.
- Delivery partners can only change orders assigned to them. Owners can only change their own restaurant's orders. Anyone else gets `404`, so order ids can't be probed.

## 💳 Dummy payment & refunds
- Placing an order writes a `payment` ledger entry (`MOCKPAY-…` reference) and sets `payment_status = mock_paid`. Prices always come from the database, never from the client.
- Cancelling or rejecting an order writes a `refund` entry and sets `payment_status = refunded`.
- Returns can be requested only for `DELIVERED` orders, need a reason of at least 10 characters, and are limited to one per order. **Approve** → `return_status=approved`, `payment_status=refunded`, a refund ledger entry, and order status `REFUNDED`. **Reject** → `return_status=rejected`.

## 🤖 AI Order Insights
- `POST /api/ai/insights` with `{ "mode": "summary" }` or `{ "mode": "question", "question": "How much did I spend this week?" }`.
- The backend reads the **authenticated customer's orders only**. The customer id comes from the JWT, never from the request. It builds a compact JSON context: up to 30 recent orders plus pre-computed totals such as weekly spend, undelivered orders and most-ordered items. That context goes to OpenAI with a system prompt that restricts answers to the provided data. Another customer's data is never in the prompt, so it can't leak.
- The key stays in a backend environment variable and is never sent to the browser.
- Errors and rate limits:
  - Each customer gets a per-minute limit (`429` with a `Retry-After` header).
  - The OpenAI SDK retries automatically.
  - OpenAI rate-limit, quota, authentication, timeout and connection errors are turned into clear `429/502/503/504` messages.
  - Without a key, the endpoint returns `503`. `GET /api/ai/stats` still serves the locally computed statistics.

## ⏰ Middleware & background tasks
- `RequestLoggingMiddleware` logs `METHOD /path -> status (ms) [request-id]`, adds `X-Process-Time` and `X-Request-ID` headers, and turns unhandled errors into a JSON 500 response.
- On startup, an asyncio task scans every `REMINDER_SCAN_INTERVAL_SECONDS` for orders in `PLACED`/`ACCEPTED` whose status hasn't changed for more than `REMINDER_THRESHOLD_MINUTES`. It writes one `admin_reminder_logs` row per stale order and status, without duplicates. Reminders resolve automatically when the order moves on, and owners can also dismiss them. `POST /api/owner/reminders/scan` runs the same scan right away through FastAPI `BackgroundTasks`.

---

## 📚 API reference

The full interactive documentation (schemas, try-it-out) is at **`/docs`**. Click **Authorize** and log in with a demo account. All paths below start with `/api`. 🔒 = needs a JWT. The role column shows who is allowed.

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Register (owners also create their restaurant) |
| POST | `/auth/login` | public | Log in with JSON → JWT + user |
| POST | `/auth/token` | public | OAuth2 form login (used by Swagger) |
| GET | `/auth/me` | 🔒 any | Current user |
| GET | `/restaurants` | public | List restaurants (`q`, `cuisine`, `open_only`, `page`, `page_size`) |
| GET | `/restaurants/cuisines` | public | Distinct cuisines |
| GET | `/restaurants/{id}` | public | Restaurant details + rating |
| GET | `/restaurants/{id}/menu` | public | Menu (`q`, `min_price`, `max_price`, `category`, `available_only`, `sort`) |
| GET | `/restaurants/{id}/categories` | public | Menu categories |
| GET | `/restaurants/{id}/reviews` | public | Paginated reviews |
| GET | `/dishes` | public | Search dishes across restaurants by name/price |
| POST | `/orders` | 🔒 customer | Place an order (dummy payment) |
| GET | `/orders` | 🔒 customer | My orders (`status`, `date_from`, `date_to`, pagination) |
| GET | `/orders/{id}` | 🔒 related user | Order detail + timeline + ledger |
| POST | `/orders/{id}/cancel` | 🔒 customer | Cancel (PLACED only) |
| POST | `/orders/{id}/review` | 🔒 customer | Review a delivered order |
| POST | `/orders/{id}/return` | 🔒 customer | Request a return/refund |
| GET / PATCH | `/owner/restaurant` | 🔒 owner | View / update restaurant (incl. open/closed) |
| GET / POST | `/owner/menu` | 🔒 owner | List / add dishes |
| GET / PUT / DELETE | `/owner/menu/{id}` | 🔒 owner | View / update / delete dish |
| PATCH | `/owner/menu/{id}/availability` | 🔒 owner | Mark available / unavailable |
| GET | `/owner/orders` | 🔒 owner | Restaurant orders (`status`, `date_from`, `date_to`, pagination) |
| GET | `/owner/orders/{id}` | 🔒 owner | Order detail |
| PATCH | `/owner/orders/{id}/status` | 🔒 owner | ACCEPTED / PREPARING / READY / CANCELLED |
| GET | `/owner/delivery-partners` | 🔒 owner | Partners with active-delivery counts |
| POST | `/owner/orders/{id}/assign` | 🔒 owner | Assign partner (READY → ASSIGNED) |
| GET | `/owner/returns` | 🔒 owner | Return requests (`return_status`) |
| POST | `/owner/returns/{id}/decision` | 🔒 owner | `{"decision": "approve" \| "reject", "note"}` |
| GET | `/owner/stats` | 🔒 owner | Restaurant statistics |
| GET | `/owner/reminders` | 🔒 owner | Stale-order reminders |
| POST | `/owner/reminders/scan` | 🔒 owner | Trigger a background scan (202) |
| POST | `/owner/reminders/{id}/resolve` | 🔒 owner | Dismiss a reminder |
| GET | `/delivery/orders` | 🔒 delivery | Assigned orders (`scope=active\|history\|all`, `status`, dates) |
| GET | `/delivery/orders/{id}` | 🔒 delivery | Assigned order incl. customer details |
| PATCH | `/delivery/orders/{id}/status` | 🔒 delivery | OUT_FOR_DELIVERY / DELIVERED |
| GET | `/delivery/stats` | 🔒 delivery | Active / delivered counts |
| GET | `/ai/stats` | 🔒 customer | Local order statistics |
| POST | `/ai/insights` | 🔒 customer | AI summary / Q&A over own orders |
| GET | `/health`, `/meta` | public | Health check, public config (delivery fee, AI enabled) |

Paginated responses look like `{ "items": [...], "total": 42, "page": 1, "page_size": 10, "pages": 5 }`. Errors look like `{ "detail": "message" }`. Status codes used: `400/401/403/404/409/422/429/5xx`.

---

## ☁️ Deployment notes
- **Backend:** the Docker image runs on any container host (Render, Railway, Fly.io, Azure Container Apps, ECS). Set the environment variables listed above, point `DATABASE_URL` at a managed PostgreSQL database (`postgresql+psycopg://user:pass@host:5432/db`), and set `CORS_ORIGINS` to the frontend URL.
- **Frontend:** run `npm run build` and deploy `frontend/dist` to any static host (Vercel, Netlify, S3). Set `VITE_API_BASE_URL` at build time, and configure SPA fallback so every route is served `index.html`.
- **Production:** use a strong `JWT_SECRET_KEY` and set `SEED_DEMO_DATA=false`.

## ⚠️ Known limitations
- The AI rate limiter is in memory and per process. Use Redis if you run several backend replicas.
- The schema is created with `create_all`. Add Alembic migrations before changing the schema in production.
- Date filters use UTC calendar days.
