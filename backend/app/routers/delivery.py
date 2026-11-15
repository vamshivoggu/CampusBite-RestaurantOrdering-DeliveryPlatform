"""Delivery-partner endpoints. Partners only ever see orders assigned to them."""
from datetime import datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, OrderStatus, utcnow
from ..schemas import DeliveryStats, DeliveryStatusUpdate, OrderDetailOut, OrderOut, Page
from ..security import DeliveryUser
from ..services.order_workflow import ORDER_LOAD_OPTIONS, change_status, load_order
from ..utils import OrderFilters, PageParams, apply_order_filters, order_filters, page_params, paginate

router = APIRouter(prefix="/delivery", tags=["Delivery Partner"])

ACTIVE = (OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY)
DONE = (OrderStatus.DELIVERED, OrderStatus.REFUNDED)


def _assigned_order(db: Session, order_id: int, partner_id: int) -> Order:
    order = load_order(db, order_id, detail=True)
    if order is None or order.delivery_partner_id != partner_id:
        raise HTTPException(404, "Order not found")
    return order


@router.get("/orders", response_model=Page[OrderOut])
def my_deliveries(
    partner: DeliveryUser,
    scope: Literal["active", "history", "all"] = Query("active", description="active = to deliver, history = delivered"),
    filters: OrderFilters = Depends(order_filters),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = select(Order).where(Order.delivery_partner_id == partner.id)
    if scope == "active":
        stmt = stmt.where(Order.status.in_(ACTIVE))
    elif scope == "history":
        stmt = stmt.where(Order.status.in_(DONE))
    stmt = apply_order_filters(stmt, filters)
    if scope == "history":
        stmt = stmt.order_by(Order.delivered_at.desc(), Order.id.desc())
    else:
        stmt = stmt.order_by(Order.status_updated_at.asc(), Order.id)
    items, total = paginate(db, stmt, params, options=ORDER_LOAD_OPTIONS)
    return Page.build(items, total, params.page, params.page_size)


@router.get("/stats", response_model=DeliveryStats)
def delivery_stats(partner: DeliveryUser, db: Session = Depends(get_db)):
    today_start = datetime.combine(utcnow().date(), time.min)
    active, delivered, today = db.execute(
        select(
            func.coalesce(func.sum(case((Order.status.in_(ACTIVE), 1), else_=0)), 0),
            func.coalesce(func.sum(case((Order.status.in_(DONE), 1), else_=0)), 0),
            func.coalesce(func.sum(case((Order.delivered_at >= today_start, 1), else_=0)), 0),
        ).where(Order.delivery_partner_id == partner.id)
    ).one()
    return DeliveryStats(active=int(active), delivered=int(delivered), delivered_today=int(today))


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
def delivery_detail(order_id: int, partner: DeliveryUser, db: Session = Depends(get_db)):
    """Includes customer name, phone and delivery address."""
    return _assigned_order(db, order_id, partner.id)


@router.patch("/orders/{order_id}/status", response_model=OrderDetailOut)
def update_delivery_status(order_id: int, payload: DeliveryStatusUpdate, partner: DeliveryUser,
                           db: Session = Depends(get_db)):
    """ASSIGNED → OUT_FOR_DELIVERY → DELIVERED. Anything else is rejected with 409."""
    order = _assigned_order(db, order_id, partner.id)
    change_status(db, order, OrderStatus(payload.status), partner, note=payload.note)
    db.commit()
    return load_order(db, order.id, detail=True)
