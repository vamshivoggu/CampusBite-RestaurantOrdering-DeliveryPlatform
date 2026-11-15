"""End-to-end API tests covering auth, RBAC, the order lifecycle, payments, returns, reminders and AI."""
from datetime import timedelta

from app.database import SessionLocal
from app.models import Order, OrderStatus, ReminderLog, utcnow
from app.services.reminders import scan_stale_orders

from .conftest import login


def _owner_restaurant_id(client, owner):
    return client.get("/api/owner/restaurant", headers=owner).json()["id"]


def _place(client, customer, restaurant_id, qty=2):
    menu = client.get(f"/api/restaurants/{restaurant_id}/menu", params={"available_only": True}).json()["items"]
    r = client.post("/api/orders", headers=customer, json={
        "restaurant_id": restaurant_id,
        "items": [{"menu_item_id": menu[0]["id"], "quantity": qty}],
        "delivery_address": "Room 1, Hostel A",
        "payment_method": "mock_upi",
    })
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- auth
def test_register_login_and_me(client):
    r = client.post("/api/auth/register", json={
        "name": "New Student", "email": "new@campus.dev", "password": "abc12345", "role": "customer"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "new@campus.dev"
    assert client.post("/api/auth/register", json={
        "name": "Dup", "email": "NEW@campus.dev", "password": "abc12345"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "new@campus.dev", "password": "wrong123"}).status_code == 401


def test_weak_password_and_owner_requires_restaurant(client):
    assert client.post("/api/auth/register", json={"name": "X Y", "email": "a@b.dev", "password": "short"}).status_code == 422
    r = client.post("/api/auth/register", json={
        "name": "Owner X", "email": "ox@b.dev", "password": "abc12345", "role": "restaurant_owner"})
    assert r.status_code == 422


def test_owner_registration_creates_restaurant(client):
    r = client.post("/api/auth/register", json={
        "name": "Owner New", "email": "ownernew@b.dev", "password": "abc12345",
        "role": "restaurant_owner", "restaurant_name": "Test Tiffins"})
    assert r.status_code == 201
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/owner/restaurant", headers=h).json()["name"] == "Test Tiffins"


def test_protected_routes_need_token_and_role(client, customer, owner, rider):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/orders", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/api/owner/orders", headers=customer).status_code == 403
    assert client.get("/api/delivery/orders", headers=owner).status_code == 403
    assert client.post("/api/orders", headers=rider, json={}).status_code in (403, 422)
    assert client.post("/api/ai/insights", headers=owner, json={"mode": "summary"}).status_code == 403


# ---------------------------------------------------------------- browsing
def test_browse_and_search(client):
    page = client.get("/api/restaurants", params={"page_size": 2}).json()
    assert page["total"] >= 3 and len(page["items"]) == 2 and page["pages"] >= 2
    rid = page["items"][0]["id"]
    menu = client.get(f"/api/restaurants/{rid}/menu", params={"min_price": 100, "max_price": 150, "sort": "price_asc"}).json()
    prices = [m["price"] for m in menu["items"]]
    assert prices == sorted(prices) and all(100 <= p <= 150 for p in prices)
    dishes = client.get("/api/dishes", params={"q": "burger"}).json()
    assert dishes["total"] >= 2 and all("burger" in d["name"].lower() for d in dishes["items"])
    assert client.get("/api/restaurants/99999").status_code == 404


# ---------------------------------------------------------------- full lifecycle
def test_full_order_lifecycle(client, customer, owner, rider, rider2):
    rid = _owner_restaurant_id(client, owner)
    order = _place(client, customer, rid)
    oid = order["id"]
    assert order["status"] == "PLACED" and order["payment_status"] == "mock_paid"
    assert order["total_amount"] == round(order["subtotal"] + order["delivery_fee"], 2)
    assert order["ledger_entries"][0]["entry_type"] == "payment"

    # invalid jumps are rejected
    r = client.patch(f"/api/owner/orders/{oid}/status", headers=owner, json={"status": "READY"})
    assert r.status_code == 409
    # cannot assign before READY
    partners = client.get("/api/owner/delivery-partners", headers=owner).json()
    rider_id = next(p["id"] for p in partners if p["email"] == "rider@campusbite.dev")
    assert client.post(f"/api/owner/orders/{oid}/assign", headers=owner, json={"delivery_partner_id": rider_id}).status_code == 409

    for st in ("ACCEPTED", "PREPARING", "READY"):
        r = client.patch(f"/api/owner/orders/{oid}/status", headers=owner, json={"status": st})
        assert r.status_code == 200, r.text
    # customer can no longer cancel
    assert client.post(f"/api/orders/{oid}/cancel", headers=customer).status_code == 409

    r = client.post(f"/api/owner/orders/{oid}/assign", headers=owner, json={"delivery_partner_id": rider_id})
    assert r.status_code == 200 and r.json()["status"] == "ASSIGNED"

    # other rider cannot see / update it
    assert client.patch(f"/api/delivery/orders/{oid}/status", headers=rider2, json={"status": "OUT_FOR_DELIVERY"}).status_code == 404
    # rider cannot skip OUT_FOR_DELIVERY
    assert client.patch(f"/api/delivery/orders/{oid}/status", headers=rider, json={"status": "DELIVERED"}).status_code == 409
    # rider sees customer delivery details
    d = client.get(f"/api/delivery/orders/{oid}", headers=rider).json()
    assert d["delivery_address"] and d["customer"]["name"]
    assert client.patch(f"/api/delivery/orders/{oid}/status", headers=rider, json={"status": "OUT_FOR_DELIVERY"}).status_code == 200
    r = client.patch(f"/api/delivery/orders/{oid}/status", headers=rider, json={"status": "DELIVERED"})
    assert r.status_code == 200 and r.json()["delivered_at"]
    assert [h["to_status"] for h in r.json()["history"]] == [
        "PLACED", "ACCEPTED", "PREPARING", "READY", "ASSIGNED", "OUT_FOR_DELIVERY", "DELIVERED"]

    # delivered orders cannot be cancelled
    assert client.post(f"/api/orders/{oid}/cancel", headers=customer).status_code == 409
    history = client.get("/api/delivery/orders", headers=rider, params={"scope": "history"}).json()
    assert any(o["id"] == oid for o in history["items"])

    # review once
    assert client.post(f"/api/orders/{oid}/review", headers=customer, json={"rating": 5, "comment": "Great"}).status_code == 201
    assert client.post(f"/api/orders/{oid}/review", headers=customer, json={"rating": 4}).status_code == 409

    # return -> approve -> refunded
    assert client.post(f"/api/orders/{oid}/return", headers=customer, json={"reason": "short"}).status_code == 422
    r = client.post(f"/api/orders/{oid}/return", headers=customer, json={"reason": "Food arrived cold and soggy"})
    assert r.status_code == 200 and r.json()["return_status"] == "requested"
    assert client.post(f"/api/orders/{oid}/return", headers=customer, json={"reason": "Asking a second time"}).status_code == 409
    r = client.post(f"/api/owner/returns/{oid}/decision", headers=owner, json={"decision": "approve", "note": "Sorry!"})
    assert r.status_code == 200
    body = r.json()
    assert body["return_status"] == "approved" and body["payment_status"] == "refunded" and body["status"] == "REFUNDED"
    assert [e["entry_type"] for e in body["ledger_entries"]] == ["payment", "refund"]


def test_cancel_and_reject_refund(client, customer, owner):
    rid = _owner_restaurant_id(client, owner)
    o = _place(client, customer, rid)
    r = client.post(f"/api/orders/{o['id']}/cancel", headers=customer)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED" and r.json()["payment_status"] == "refunded"
    assert client.post(f"/api/orders/{o['id']}/return", headers=customer, json={"reason": "Want my money back"}).status_code == 409


def test_return_reject(client, customer):
    owner2 = login(client, "owner2@campusbite.dev")
    pending = client.get("/api/owner/returns", headers=owner2, params={"return_status": "requested"}).json()["items"]
    assert pending, "seeded return request expected"
    oid = pending[0]["id"]
    r = client.post(f"/api/owner/returns/{oid}/decision", headers=owner2, json={"decision": "reject", "note": "Photo needed"})
    assert r.status_code == 200 and r.json()["return_status"] == "rejected" and r.json()["payment_status"] == "mock_paid"
    assert client.post(f"/api/owner/returns/{oid}/decision", headers=owner2, json={"decision": "approve"}).status_code == 409


# ---------------------------------------------------------------- data isolation
def test_users_cannot_access_others_orders(client, customer, customer2, owner, owner2):
    rid = _owner_restaurant_id(client, owner)
    o = _place(client, customer, rid)
    assert client.get(f"/api/orders/{o['id']}", headers=customer2).status_code == 404
    assert client.post(f"/api/orders/{o['id']}/cancel", headers=customer2).status_code == 404
    assert client.get(f"/api/owner/orders/{o['id']}", headers=owner2).status_code == 404
    assert client.patch(f"/api/owner/orders/{o['id']}/status", headers=owner2, json={"status": "ACCEPTED"}).status_code == 404
    mine = client.get("/api/orders", headers=customer2).json()["items"]
    assert all(x["customer"]["id"] != o["customer"]["id"] for x in mine)


def test_cannot_order_unavailable_or_foreign_dish(client, customer, owner, owner2):
    rid = _owner_restaurant_id(client, owner)
    dish = client.post("/api/owner/menu", headers=owner, json={"name": "Seasonal Special", "price": 199}).json()
    client.patch(f"/api/owner/menu/{dish['id']}/availability", headers=owner, json={"is_available": False})
    r = client.post("/api/orders", headers=customer, json={
        "restaurant_id": rid, "items": [{"menu_item_id": dish["id"], "quantity": 1}], "delivery_address": "Hostel 1"})
    assert r.status_code == 409
    other_rid = _owner_restaurant_id(client, owner2)
    r = client.post("/api/orders", headers=customer, json={
        "restaurant_id": other_rid, "items": [{"menu_item_id": dish["id"], "quantity": 1}], "delivery_address": "Hostel 1"})
    assert r.status_code == 422
    # owner2 cannot edit owner1's dish
    assert client.put(f"/api/owner/menu/{dish['id']}", headers=owner2, json={"price": 1}).status_code == 404
    assert client.delete(f"/api/owner/menu/{dish['id']}", headers=owner).status_code == 204


# ---------------------------------------------------------------- dashboards
def test_filters_pagination_and_stats(client, customer, owner):
    r = client.get("/api/orders", headers=customer, params={"status": ["DELIVERED", "REFUNDED"], "page_size": 2})
    data = r.json()
    assert r.status_code == 200 and len(data["items"]) <= 2
    assert all(o["status"] in ("DELIVERED", "REFUNDED") for o in data["items"])
    today = utcnow().date().isoformat()
    r = client.get("/api/owner/orders", headers=owner, params={"date_from": today, "date_to": today})
    assert r.status_code == 200
    assert client.get("/api/owner/orders", headers=owner, params={"date_from": "2026-02-02", "date_to": "2026-01-01"}).status_code == 422
    stats = client.get("/api/owner/stats", headers=owner).json()
    assert stats["total_orders"] > 0 and len(stats["last_7_days"]) == 7 and stats["top_items"]


def test_reminders_background_scan(client, owner):
    rid = _owner_restaurant_id(client, owner)
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.restaurant_id == rid, Order.status == OrderStatus.PLACED).first()
        order.status_updated_at = utcnow() - timedelta(minutes=30)
        db.commit()
        oid = order.id
        scan_stale_orders(db)
        scan_stale_orders(db)  # idempotent
        assert db.query(ReminderLog).filter(ReminderLog.order_id == oid, ReminderLog.is_resolved.is_(False)).count() == 1
    rem = client.get("/api/owner/reminders", headers=owner).json()["items"]
    assert any(r["order_id"] == oid for r in rem)
    assert client.post("/api/owner/reminders/scan", headers=owner).status_code == 202
    # updating the order resolves its reminder
    client.patch(f"/api/owner/orders/{oid}/status", headers=owner, json={"status": "ACCEPTED"})
    rem = client.get("/api/owner/reminders", headers=owner).json()["items"]
    assert not any(r["order_id"] == oid for r in rem)


# ---------------------------------------------------------------- AI
def test_ai_without_key_returns_503_and_stats_work(client, customer):
    r = client.post("/api/ai/insights", headers=customer, json={"mode": "question", "question": "How much did I spend?"})
    assert r.status_code == 503
    assert client.post("/api/ai/insights", headers=customer, json={"mode": "question"}).status_code == 422
    stats = client.get("/api/ai/stats", headers=customer).json()
    assert stats["total_orders"] > 0 and "most_ordered_items" in stats


def test_ai_context_only_contains_own_orders(client, customer):
    from app.models import User
    from app.services.ai_insights import build_context, fetch_customer_orders

    with SessionLocal() as db:
        asha = db.query(User).filter(User.email == "customer@campusbite.dev").one()
        orders = fetch_customer_orders(db, asha.id)
        ctx = build_context(orders)
        ids = {o["order_id"] for o in ctx["recent_orders_newest_first"]}
        owners = {o.customer_id for o in db.query(Order).filter(Order.id.in_(ids))}
        assert owners == {asha.id}


def test_ai_with_mocked_openai(client, customer, monkeypatch):
    from app.services import ai_insights

    captured = {}

    def fake_ask(question, context):
        captured["ctx"] = context
        return "You ordered burgers most often."

    monkeypatch.setattr(ai_insights, "ask_openai", fake_ask)
    r = client.post("/api/ai/insights", headers=customer, json={"mode": "summary"})
    assert r.status_code == 200 and "burgers" in r.json()["answer"]
    assert captured["ctx"]["stats"]["total_orders"] > 0


def test_middleware_headers(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and "X-Process-Time" in r.headers and "X-Request-ID" in r.headers
