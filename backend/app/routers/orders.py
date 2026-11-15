"""Customer order endpoints + shared order detail."""
from collections import OrderedDict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import MenuItem, Order, OrderItem, OrderStatus, OrderStatusHistory, Restaurant, ReturnStatus, Review, utcnow
from ..schemas import OrderCreate, OrderDetailOut, OrderOut, Page, ReturnRequestCreate, ReviewCreate, ReviewOut
from ..security import CurrentUser, CustomerUser
from ..services.order_workflow import (
    ORDER_LOAD_OPTIONS,
    change_status,
    load_order,
    money,
    record_mock_payment,
    record_refund,
    user_can_view_order,
)
from ..utils import OrderFilters, PageParams, apply_order_filters, order_filters, page_params, paginate

router = APIRouter(prefix="/orders", tags=["Orders"])


def _own_order(db: Session, order_id: int, customer_id: int, detail: bool = False) -> Order:
    order = load_order(db, order_id, detail)
    # 404 (not 403) so customers cannot probe which order ids exist.
    if order is None or order.customer_id != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post("", response_model=OrderDetailOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, customer: CustomerUser, db: Session = Depends(get_db)):
    """Place an order. Prices are always taken from the database, never from the client.
    The dummy payment is recorded immediately and the order becomes `mock_paid`."""
    restaurant = db.get(Restaurant, payload.restaurant_id)
    if restaurant is None:
        raise HTTPException(404, "Restaurant not found")
    if not restaurant.is_open:
        raise HTTPException(409, f"{restaurant.name} is currently closed")

    # merge duplicate lines
    quantities: OrderedDict[int, int] = OrderedDict()
    for line in payload.items:
        quantities[line.menu_item_id] = quantities.get(line.menu_item_id, 0) + line.quantity
    if any(q > 50 for q in quantities.values()):
        raise HTTPException(422, "Maximum quantity per dish is 50")

    menu_items = {m.id: m for m in db.scalars(select(MenuItem).where(MenuItem.id.in_(quantities.keys()))).all()}
    order_items: list[OrderItem] = []
    subtotal = Decimal("0")
    for item_id, qty in quantities.items():
        mi = menu_items.get(item_id)
        if mi is None or mi.restaurant_id != restaurant.id:
            raise HTTPException(422, f"Dish {item_id} does not belong to {restaurant.name}")
        if not mi.is_available:
            raise HTTPException(409, f"'{mi.name}' is currently unavailable")
        line_total = money(mi.price) * qty
        subtotal += line_total
        order_items.append(OrderItem(menu_item_id=mi.id, name=mi.name, unit_price=money(mi.price),
                                     quantity=qty, subtotal=money(line_total)))

    fee = money(settings.delivery_fee)
    order = Order(
        customer_id=customer.id, restaurant_id=restaurant.id, status=OrderStatus.PLACED,
        payment_method=payload.payment_method, subtotal=money(subtotal), delivery_fee=fee,
        total_amount=money(subtotal + fee), delivery_address=payload.delivery_address.strip(),
        notes=(payload.notes or "").strip() or None, items=order_items,
    )
    db.add(order)
    db.flush()
    db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.PLACED,
                              changed_by_id=customer.id, changed_by_role=customer.role.value, note="Order placed"))
    record_mock_payment(db, order)
    db.commit()
    return load_order(db, order.id, detail=True)


@router.get("", response_model=Page[OrderOut])
def my_orders(
    customer: CustomerUser,
    filters: OrderFilters = Depends(order_filters),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    """The logged-in customer's order history, filterable by status and date."""
    stmt = apply_order_filters(select(Order).where(Order.customer_id == customer.id), filters)
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc())
    items, total = paginate(db, stmt, params, options=ORDER_LOAD_OPTIONS)
    return Page.build(items, total, params.page, params.page_size)


@router.get("/{order_id}", response_model=OrderDetailOut)
def order_detail(order_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    """Order detail + status timeline. Visible to the customer who placed it, the restaurant's
    owner, and the assigned delivery partner only."""
    order = load_order(db, order_id, detail=True)
    if order is None or not user_can_view_order(user, order):
        raise HTTPException(404, "Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderDetailOut)
def cancel_order(order_id: int, customer: CustomerUser, db: Session = Depends(get_db)):
    order = _own_order(db, order_id, customer.id)
    if order.status != OrderStatus.PLACED:
        raise HTTPException(409, f"Orders can only be cancelled while PLACED (current status: {order.status.value})")
    change_status(db, order, OrderStatus.CANCELLED, customer, note="Cancelled by customer")
    record_refund(db, order, note="Automatic refund for cancelled order")
    db.commit()
    return load_order(db, order.id, detail=True)


@router.post("/{order_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def review_order(order_id: int, payload: ReviewCreate, customer: CustomerUser, db: Session = Depends(get_db)):
    order = _own_order(db, order_id, customer.id)
    if order.status not in (OrderStatus.DELIVERED, OrderStatus.REFUNDED):
        raise HTTPException(409, "You can review an order only after it has been delivered")
    if order.review is not None:
        raise HTTPException(409, "This order has already been reviewed")
    review = Review(order_id=order.id, customer_id=customer.id, restaurant_id=order.restaurant_id,
                    rating=payload.rating, comment=(payload.comment or "").strip() or None)
    db.add(review)
    try:
        db.commit()
    except IntegrityError:  # race on the unique order_id constraint
        db.rollback()
        raise HTTPException(409, "This order has already been reviewed")
    return review


@router.post("/{order_id}/return", response_model=OrderDetailOut)
def request_return(order_id: int, payload: ReturnRequestCreate, customer: CustomerUser, db: Session = Depends(get_db)):
    order = _own_order(db, order_id, customer.id)
    if order.return_status != ReturnStatus.NONE:
        raise HTTPException(409, "A return/refund request already exists for this order")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(409, "Returns can only be requested for delivered orders")
    order.return_status = ReturnStatus.REQUESTED
    order.return_reason = payload.reason
    order.return_requested_at = utcnow()
    db.commit()
    return load_order(db, order.id, detail=True)
