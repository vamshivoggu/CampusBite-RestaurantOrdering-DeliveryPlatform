"""Order lifecycle state machine, dummy payments and refunds.

Every status change in the system goes through `change_status`, so invalid transitions and
role violations are rejected in one place regardless of which endpoint is used.
"""
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from ..models import (
    LedgerEntryType,
    Order,
    OrderStatus,
    OrderStatusHistory,
    PaymentLedger,
    PaymentStatus,
    ReminderLog,
    User,
    UserRole,
    utcnow,
)

S = OrderStatus
CUSTOMER, OWNER, DELIVERY = UserRole.CUSTOMER, UserRole.RESTAURANT_OWNER, UserRole.DELIVERY_PARTNER

# (from, to) -> roles allowed to perform the transition
TRANSITIONS: dict[tuple[OrderStatus, OrderStatus], set[UserRole]] = {
    (S.PLACED, S.ACCEPTED): {OWNER},
    (S.PLACED, S.CANCELLED): {CUSTOMER, OWNER},  # customer cancels / owner rejects
    (S.ACCEPTED, S.PREPARING): {OWNER},
    (S.PREPARING, S.READY): {OWNER},
    (S.READY, S.ASSIGNED): {OWNER},
    (S.ASSIGNED, S.OUT_FOR_DELIVERY): {DELIVERY},
    (S.OUT_FOR_DELIVERY, S.DELIVERED): {DELIVERY},
    (S.DELIVERED, S.REFUNDED): {OWNER},  # only through an approved return request
}

ACTIVE_STATUSES = (S.PLACED, S.ACCEPTED, S.PREPARING, S.READY, S.ASSIGNED, S.OUT_FOR_DELIVERY)

ORDER_LOAD_OPTIONS = [
    selectinload(Order.items),
    selectinload(Order.customer),
    selectinload(Order.restaurant),
    selectinload(Order.delivery_partner),
    selectinload(Order.review),
]
ORDER_DETAIL_OPTIONS = ORDER_LOAD_OPTIONS + [selectinload(Order.history), selectinload(Order.ledger_entries)]


def allowed_next_statuses(current: OrderStatus, role: UserRole) -> list[OrderStatus]:
    return [to for (frm, to), roles in TRANSITIONS.items() if frm == current and role in roles]


def change_status(db: Session, order: Order, new_status: OrderStatus, actor: User, note: str | None = None) -> Order:
    """Validate and apply a status transition, recording history. Caller commits."""
    roles = TRANSITIONS.get((order.status, new_status))
    if roles is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Invalid status transition: {order.status.value} -> {new_status.value}",
        )
    if actor.role not in roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Role '{actor.role.value}' cannot move an order from {order.status.value} to {new_status.value}",
        )
    now = utcnow()
    db.add(OrderStatusHistory(
        order_id=order.id, from_status=order.status, to_status=new_status,
        changed_by_id=actor.id, changed_by_role=actor.role.value, note=note,
    ))
    order.status = new_status
    order.status_updated_at = now
    if new_status == S.DELIVERED:
        order.delivered_at = now
    # Any pending "stale order" reminders are no longer relevant once the order moves.
    db.execute(
        update(ReminderLog)
        .where(ReminderLog.order_id == order.id, ReminderLog.is_resolved.is_(False))
        .values(is_resolved=True, resolved_at=now)
    )
    return order


def _reference(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def record_mock_payment(db: Session, order: Order) -> PaymentLedger:
    """Dummy payment: always succeeds, writes a ledger entry and marks the order mock_paid."""
    entry = PaymentLedger(
        order_id=order.id, entry_type=LedgerEntryType.PAYMENT, amount=order.total_amount,
        status="success", method=order.payment_method, reference=_reference("MOCKPAY"),
        note="Dummy payment - no real money was charged",
    )
    db.add(entry)
    order.payment_status = PaymentStatus.MOCK_PAID
    return entry


def record_refund(db: Session, order: Order, note: str) -> PaymentLedger | None:
    """Refund a mock-paid order (idempotent: does nothing if it was not paid)."""
    if order.payment_status != PaymentStatus.MOCK_PAID:
        return None
    entry = PaymentLedger(
        order_id=order.id, entry_type=LedgerEntryType.REFUND, amount=order.total_amount,
        status="success", method=order.payment_method, reference=_reference("MOCKREF"), note=note,
    )
    db.add(entry)
    order.payment_status = PaymentStatus.REFUNDED
    return entry


def load_order(db: Session, order_id: int, detail: bool = False) -> Order | None:
    opts = ORDER_DETAIL_OPTIONS if detail else ORDER_LOAD_OPTIONS
    # populate_existing refreshes objects/collections already in the session (e.g. after a status change)
    return db.scalar(select(Order).where(Order.id == order_id).options(*opts).execution_options(populate_existing=True))


def user_can_view_order(user: User, order: Order) -> bool:
    if user.role == CUSTOMER:
        return order.customer_id == user.id
    if user.role == DELIVERY:
        return order.delivery_partner_id == user.id
    if user.role == OWNER:
        return order.restaurant.owner_id == user.id
    return False


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))
