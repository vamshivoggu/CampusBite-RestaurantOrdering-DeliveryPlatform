"""Restaurant-owner endpoints: restaurant profile, menu, orders, partners, returns, stats, reminders.

Every query is scoped to the owner's own restaurant (resolved from the JWT), so owners can never
read or modify another restaurant's data.
"""
from datetime import datetime, time, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    ReminderLog,
    ReturnStatus,
    Review,
    User,
    UserRole,
    utcnow,
)
from ..schemas import (
    AssignPartnerRequest,
    AvailabilityUpdate,
    DailyPoint,
    DeliveryPartnerOut,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    Message,
    OrderDetailOut,
    OrderOut,
    OwnerStatusUpdate,
    Page,
    ReminderOut,
    RestaurantOut,
    RestaurantStats,
    RestaurantUpdate,
    ReturnDecision,
    StatusCount,
    TopItem,
)
from ..security import OwnerRestaurant, OwnerUser
from ..services.order_workflow import (
    ACTIVE_STATUSES,
    ORDER_LOAD_OPTIONS,
    change_status,
    load_order,
    money,
    record_refund,
)
from ..services.reminders import run_scan
from ..utils import OrderFilters, PageParams, apply_order_filters, order_filters, page_params, paginate
from .restaurants import ratings_for, restaurant_out

router = APIRouter(prefix="/owner", tags=["Restaurant Owner"])


def _restaurant_order(db: Session, order_id: int, restaurant_id: int, detail: bool = True) -> Order:
    order = load_order(db, order_id, detail)
    if order is None or order.restaurant_id != restaurant_id:
        raise HTTPException(404, "Order not found")
    return order


def _restaurant_item(db: Session, item_id: int, restaurant_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if item is None or item.restaurant_id != restaurant_id:
        raise HTTPException(404, "Dish not found")
    return item


# ------------------------------------------------------------------ restaurant profile
@router.get("/restaurant", response_model=RestaurantOut)
def my_restaurant(restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    return restaurant_out(restaurant, ratings_for(db, [restaurant.id]))


@router.patch("/restaurant", response_model=RestaurantOut)
def update_restaurant(payload: RestaurantUpdate, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(restaurant, k, v)
    db.commit()
    return restaurant_out(restaurant, ratings_for(db, [restaurant.id]))


# ------------------------------------------------------------------ menu management
@router.get("/menu", response_model=Page[MenuItemOut])
def list_menu(
    restaurant: OwnerRestaurant,
    q: str | None = Query(None, max_length=100),
    available: bool | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(MenuItem.name.ilike(like), MenuItem.category.ilike(like)))
    if available is not None:
        stmt = stmt.where(MenuItem.is_available.is_(available))
    items, total = paginate(db, stmt.order_by(MenuItem.category, MenuItem.name, MenuItem.id), params)
    return Page.build(items, total, params.page, params.page_size)


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def add_dish(payload: MenuItemCreate, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["price"] = money(data["price"])
    item = MenuItem(restaurant_id=restaurant.id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/menu/{item_id}", response_model=MenuItemOut)
def get_dish(item_id: int, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    return _restaurant_item(db, item_id, restaurant.id)


@router.put("/menu/{item_id}", response_model=MenuItemOut)
def update_dish(item_id: int, payload: MenuItemUpdate, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    item = _restaurant_item(db, item_id, restaurant.id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        if k in ("name", "price") and v is None:
            raise HTTPException(422, f"{k} cannot be null")
        setattr(item, k, money(v) if k == "price" else v)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/menu/{item_id}/availability", response_model=MenuItemOut)
def set_availability(item_id: int, payload: AvailabilityUpdate, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    item = _restaurant_item(db, item_id, restaurant.id)
    item.is_available = payload.is_available
    db.commit()
    db.refresh(item)
    return item


@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(item_id: int, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    item = _restaurant_item(db, item_id, restaurant.id)
    # keep order history intact (order_items snapshot name/price; FK is nulled)
    db.query(OrderItem).filter(OrderItem.menu_item_id == item.id).update({OrderItem.menu_item_id: None})
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ orders
@router.get("/orders", response_model=Page[OrderOut])
def restaurant_orders(
    restaurant: OwnerRestaurant,
    filters: OrderFilters = Depends(order_filters),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = apply_order_filters(select(Order).where(Order.restaurant_id == restaurant.id), filters)
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc())
    items, total = paginate(db, stmt, params, options=ORDER_LOAD_OPTIONS)
    return Page.build(items, total, params.page, params.page_size)


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
def restaurant_order(order_id: int, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    return _restaurant_order(db, order_id, restaurant.id)


@router.patch("/orders/{order_id}/status", response_model=OrderDetailOut)
def update_order_status(order_id: int, payload: OwnerStatusUpdate, owner: OwnerUser, restaurant: OwnerRestaurant,
                        db: Session = Depends(get_db)):
    """Accept (PLACED→ACCEPTED), start preparing (ACCEPTED→PREPARING), mark ready (PREPARING→READY)
    or reject (PLACED→CANCELLED). Other transitions are rejected with 409."""
    order = _restaurant_order(db, order_id, restaurant.id)
    new_status = OrderStatus(payload.status)
    change_status(db, order, new_status, owner, note=payload.note)
    if new_status == OrderStatus.CANCELLED:
        record_refund(db, order, note="Automatic refund - order rejected by restaurant")
    db.commit()
    return load_order(db, order.id, detail=True)


@router.get("/delivery-partners", response_model=list[DeliveryPartnerOut])
def delivery_partners(_: OwnerUser, db: Session = Depends(get_db)):
    active = (
        select(Order.delivery_partner_id, func.count(Order.id).label("n"))
        .where(Order.status.in_([OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY]))
        .group_by(Order.delivery_partner_id)
        .subquery()
    )
    rows = db.execute(
        select(User, func.coalesce(active.c.n, 0))
        .outerjoin(active, active.c.delivery_partner_id == User.id)
        .where(User.role == UserRole.DELIVERY_PARTNER, User.is_active.is_(True))
        .order_by(func.coalesce(active.c.n, 0), User.name)
    ).all()
    return [DeliveryPartnerOut(id=u.id, name=u.name, phone=u.phone, email=u.email, active_deliveries=n) for u, n in rows]


@router.post("/orders/{order_id}/assign", response_model=OrderDetailOut)
def assign_partner(order_id: int, payload: AssignPartnerRequest, owner: OwnerUser, restaurant: OwnerRestaurant,
                   db: Session = Depends(get_db)):
    """Assign a delivery partner to a READY order (READY → ASSIGNED)."""
    order = _restaurant_order(db, order_id, restaurant.id)
    if order.status != OrderStatus.READY:
        raise HTTPException(409, f"Delivery partners can only be assigned to READY orders (current: {order.status.value})")
    partner = db.get(User, payload.delivery_partner_id)
    if partner is None or partner.role != UserRole.DELIVERY_PARTNER or not partner.is_active:
        raise HTTPException(422, "Selected user is not an active delivery partner")
    change_status(db, order, OrderStatus.ASSIGNED, owner, note=f"Assigned to {partner.name}")
    order.delivery_partner_id = partner.id
    db.commit()
    return load_order(db, order.id, detail=True)


# ------------------------------------------------------------------ returns / refunds
@router.get("/returns", response_model=Page[OrderOut])
def return_requests(
    restaurant: OwnerRestaurant,
    return_status: ReturnStatus | None = Query(None, description="e.g. 'requested' for pending ones; omit for all"),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = select(Order).where(Order.restaurant_id == restaurant.id, Order.return_status != ReturnStatus.NONE)
    if return_status is not None:
        stmt = stmt.where(Order.return_status == return_status)
    stmt = stmt.order_by(Order.return_requested_at.desc(), Order.id.desc())
    items, total = paginate(db, stmt, params, options=ORDER_LOAD_OPTIONS)
    return Page.build(items, total, params.page, params.page_size)


@router.post("/returns/{order_id}/decision", response_model=OrderDetailOut)
def decide_return(order_id: int, payload: ReturnDecision, owner: OwnerUser, restaurant: OwnerRestaurant,
                  db: Session = Depends(get_db)):
    order = _restaurant_order(db, order_id, restaurant.id)
    if order.return_status != ReturnStatus.REQUESTED:
        raise HTTPException(409, f"There is no pending return request for this order (return status: {order.return_status.value})")
    now = utcnow()
    if payload.decision == "approve":
        change_status(db, order, OrderStatus.REFUNDED, owner, note=payload.note or "Return approved")
        record_refund(db, order, note=f"Refund for approved return. {payload.note or ''}".strip())
        order.return_status = ReturnStatus.APPROVED
    else:
        order.return_status = ReturnStatus.REJECTED
    order.return_resolved_at = now
    order.return_resolution_note = payload.note
    db.commit()
    return load_order(db, order.id, detail=True)


# ------------------------------------------------------------------ statistics
@router.get("/stats", response_model=RestaurantStats)
def restaurant_stats(restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    rid = restaurant.id
    now = utcnow()
    today_start = datetime.combine(now.date(), time.min)
    paid = Order.payment_status == PaymentStatus.MOCK_PAID

    by_status = dict(db.execute(
        select(Order.status, func.count(Order.id)).where(Order.restaurant_id == rid).group_by(Order.status)
    ).all())
    total_orders = sum(by_status.values())

    revenue, paid_count, refunded, today_orders, today_revenue = db.execute(
        select(
            func.coalesce(func.sum(case((paid, Order.total_amount), else_=0)), 0),
            func.coalesce(func.sum(case((paid, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Order.payment_status == PaymentStatus.REFUNDED, Order.total_amount), else_=0)), 0),
            func.coalesce(func.sum(case((Order.created_at >= today_start, 1), else_=0)), 0),
            func.coalesce(func.sum(case(((Order.created_at >= today_start) & paid, Order.total_amount), else_=0)), 0),
        ).where(Order.restaurant_id == rid)
    ).one()

    avg_rating, review_count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.restaurant_id == rid)
    ).one()

    menu_total, menu_available = db.execute(
        select(func.count(MenuItem.id), func.coalesce(func.sum(case((MenuItem.is_available.is_(True), 1), else_=0)), 0))
        .where(MenuItem.restaurant_id == rid)
    ).one()

    top = db.execute(
        select(OrderItem.name, func.sum(OrderItem.quantity).label("qty"), func.sum(OrderItem.subtotal))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.restaurant_id == rid, Order.status.not_in([OrderStatus.CANCELLED, OrderStatus.REFUNDED]))
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    ).all()

    week_start = datetime.combine((now - timedelta(days=6)).date(), time.min)
    day = func.date(Order.created_at)
    daily = {str(d): (n, float(r or 0)) for d, n, r in db.execute(
        select(day, func.count(Order.id), func.sum(case((paid, Order.total_amount), else_=0)))
        .where(Order.restaurant_id == rid, Order.created_at >= week_start)
        .group_by(day)
    ).all()}
    last_7 = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).date().isoformat()
        n, r = daily.get(d, (0, 0.0))
        last_7.append(DailyPoint(date=d, orders=n, revenue=round(r, 2)))

    pending_returns = db.scalar(select(func.count(Order.id)).where(
        Order.restaurant_id == rid, Order.return_status == ReturnStatus.REQUESTED)) or 0
    open_reminders = db.scalar(select(func.count(ReminderLog.id)).where(
        ReminderLog.restaurant_id == rid, ReminderLog.is_resolved.is_(False))) or 0

    return RestaurantStats(
        restaurant_id=rid,
        total_orders=total_orders,
        active_orders=sum(by_status.get(s, 0) for s in ACTIVE_STATUSES),
        delivered_orders=by_status.get(OrderStatus.DELIVERED, 0),
        cancelled_orders=by_status.get(OrderStatus.CANCELLED, 0),
        total_revenue=round(float(revenue), 2),
        refunded_amount=round(float(refunded), 2),
        average_order_value=round(float(revenue) / paid_count, 2) if paid_count else 0.0,
        orders_today=int(today_orders),
        revenue_today=round(float(today_revenue), 2),
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        review_count=review_count,
        menu_items=menu_total,
        available_menu_items=int(menu_available),
        pending_returns=pending_returns,
        open_reminders=open_reminders,
        orders_by_status=[StatusCount(status=s, count=c) for s, c in sorted(by_status.items(), key=lambda x: list(OrderStatus).index(x[0]))],
        top_items=[TopItem(name=n, quantity=int(q), revenue=round(float(r or 0), 2)) for n, q, r in top],
        last_7_days=last_7,
    )


# ------------------------------------------------------------------ reminders
@router.get("/reminders", response_model=Page[ReminderOut])
def reminders(
    restaurant: OwnerRestaurant,
    include_resolved: bool = False,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = select(ReminderLog).where(ReminderLog.restaurant_id == restaurant.id)
    if not include_resolved:
        stmt = stmt.where(ReminderLog.is_resolved.is_(False))
    items, total = paginate(db, stmt.order_by(ReminderLog.created_at.desc(), ReminderLog.id.desc()), params)
    return Page.build(items, total, params.page, params.page_size)


@router.post("/reminders/scan", response_model=Message, status_code=status.HTTP_202_ACCEPTED)
def trigger_reminder_scan(restaurant: OwnerRestaurant, background: BackgroundTasks):
    """Queue an immediate stale-order scan as a FastAPI background task (it also runs automatically every minute)."""
    background.add_task(run_scan, restaurant.id)
    return Message(message="Reminder scan started")


@router.post("/reminders/{reminder_id}/resolve", response_model=ReminderOut)
def resolve_reminder(reminder_id: int, restaurant: OwnerRestaurant, db: Session = Depends(get_db)):
    reminder = db.get(ReminderLog, reminder_id)
    if reminder is None or reminder.restaurant_id != restaurant.id:
        raise HTTPException(404, "Reminder not found")
    if not reminder.is_resolved:
        reminder.is_resolved = True
        reminder.resolved_at = utcnow()
        db.commit()
    return reminder
