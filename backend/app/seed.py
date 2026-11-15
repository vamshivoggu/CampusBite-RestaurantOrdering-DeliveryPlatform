"""Demo data so the app is usable immediately. Runs only when the users table is empty.

Run manually with:  python -m app.seed
"""
import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    Restaurant,
    ReturnStatus,
    Review,
    User,
    UserRole,
    utcnow,
)
from .security import hash_password
from .services.order_workflow import money, record_mock_payment, record_refund

logger = logging.getLogger("campusbite.seed")

DEMO_PASSWORD = "Password@123"

RESTAURANTS = [
    {
        "owner": ("Ravi Owner", "owner@campusbite.dev"),
        "name": "Campus Grill", "cuisine": "Fast Food", "address": "Food Court, Block A, Main Campus",
        "description": "Burgers, wraps and fries loved by hungry students.",
        "menu": [
            ("Classic Veg Burger", "Crispy veg patty, lettuce, house sauce", 99, "Burgers", True),
            ("Chicken Zinger Burger", "Spicy fried chicken fillet, mayo", 149, "Burgers", False),
            ("Paneer Tikka Wrap", "Smoky paneer, onions, mint chutney", 129, "Wraps", True),
            ("Chicken Shawarma Wrap", "Garlic toum, pickles, fries inside", 139, "Wraps", False),
            ("Peri Peri Fries", "Crispy fries with peri peri dust", 79, "Sides", True),
            ("Cheesy Nachos", "Loaded with cheese sauce and jalapeños", 109, "Sides", True),
            ("Cold Coffee", "Thick, creamy and chilled", 89, "Beverages", True),
            ("Oreo Shake", "Blended with vanilla ice cream", 119, "Beverages", True),
        ],
    },
    {
        "owner": ("Meera Owner", "owner2@campusbite.dev"),
        "name": "Green Bowl Café", "cuisine": "Healthy", "address": "Library Lawn Kiosk, Main Campus",
        "description": "Salads, bowls and smoothies for the health-conscious.",
        "menu": [
            ("Quinoa Power Bowl", "Quinoa, chickpeas, veggies, tahini", 189, "Bowls", True),
            ("Grilled Chicken Salad", "Greens, grilled chicken, honey mustard", 209, "Salads", False),
            ("Greek Salad", "Feta, olives, cucumber, tomato", 169, "Salads", True),
            ("Avocado Toast", "Sourdough, smashed avocado, chilli flakes", 159, "Breakfast", True),
            ("Berry Blast Smoothie", "Mixed berries, banana, yogurt", 129, "Smoothies", True),
            ("Green Detox Juice", "Spinach, apple, cucumber, lemon", 99, "Smoothies", True),
        ],
    },
    {
        "owner": ("Arjun Owner", "owner3@campusbite.dev"),
        "name": "Noodle Nook", "cuisine": "Chinese", "address": "Hostel Road, Near Gate 2",
        "description": "Wok-tossed noodles, fried rice and momos.",
        "menu": [
            ("Veg Hakka Noodles", "Classic wok-tossed noodles", 119, "Noodles", True),
            ("Chicken Schezwan Noodles", "Fiery schezwan sauce", 149, "Noodles", False),
            ("Veg Fried Rice", "With spring onions and soy", 109, "Rice", True),
            ("Egg Fried Rice", "Fluffy egg, garlic, pepper", 129, "Rice", False),
            ("Veg Steamed Momos (8)", "With spicy red chutney", 89, "Momos", True),
            ("Chicken Fried Momos (8)", "Crispy and juicy", 119, "Momos", False),
            ("Chilli Paneer", "Dry, Indo-Chinese style", 159, "Starters", True),
        ],
    },
]

CUSTOMERS = [
    ("Asha Customer", "customer@campusbite.dev", "9876500001", "Room 214, Girls Hostel 3, Main Campus"),
    ("Kabir Customer", "customer2@campusbite.dev", "9876500002", "Room 108, Boys Hostel 1, Main Campus"),
]
PARTNERS = [
    ("Dev Rider", "rider@campusbite.dev", "9876511111"),
    ("Sana Rider", "rider2@campusbite.dev", "9876522222"),
]


def _user(db: Session, name, email, role, phone=None, address=None) -> User:
    u = User(name=name, email=email, password_hash=hash_password(DEMO_PASSWORD), role=role, phone=phone, address=address)
    db.add(u)
    db.flush()
    return u


def _order(db, customer, restaurant, lines, path, minutes_ago, partner=None, actor_map=None) -> Order:
    """Create an order that walked through `path` of statuses, ending `minutes_ago` minutes in the past."""
    created = utcnow() - timedelta(minutes=minutes_ago)
    items = [OrderItem(menu_item_id=m.id, name=m.name, unit_price=m.price, quantity=q, subtotal=money(m.price * q))
             for m, q in lines]
    subtotal = sum((i.subtotal for i in items), Decimal("0"))
    fee = Decimal("30.00")
    order = Order(customer_id=customer.id, restaurant_id=restaurant.id, status=OrderStatus.PLACED,
                  subtotal=subtotal, delivery_fee=fee, total_amount=subtotal + fee,
                  delivery_address=customer.address, items=items, created_at=created,
                  updated_at=created, status_updated_at=created, payment_method="mock_upi")
    db.add(order)
    db.flush()
    record_mock_payment(db, order)
    db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.PLACED,
                              changed_by_id=customer.id, changed_by_role="customer", created_at=created))
    prev, t = OrderStatus.PLACED, created
    for st in path:
        t = t + timedelta(minutes=4)
        actor = actor_map[st]
        db.add(OrderStatusHistory(order_id=order.id, from_status=prev, to_status=st, changed_by_id=actor.id,
                                  changed_by_role=actor.role.value, created_at=t))
        prev = st
    order.status = prev
    order.status_updated_at = t if path else created
    order.updated_at = order.status_updated_at
    if partner and prev in (OrderStatus.ASSIGNED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED):
        order.delivery_partner_id = partner.id
    if prev == OrderStatus.DELIVERED:
        order.delivered_at = t
    if prev == OrderStatus.CANCELLED:
        record_refund(db, order, note="Automatic refund for cancelled order")
    return order


def seed_demo_data(db: Session) -> bool:
    if db.scalar(select(User.id).limit(1)):
        return False
    logger.info("Seeding demo data ...")

    restaurants: list[tuple[User, Restaurant, list[MenuItem]]] = []
    for spec in RESTAURANTS:
        owner = _user(db, *spec["owner"], UserRole.RESTAURANT_OWNER, phone="9800000000")
        r = Restaurant(owner_id=owner.id, name=spec["name"], cuisine=spec["cuisine"], address=spec["address"],
                       description=spec["description"], phone="9800000000", is_open=True)
        db.add(r)
        db.flush()
        items = [MenuItem(restaurant_id=r.id, name=n, description=d, price=Decimal(p), category=c, is_veg=v)
                 for n, d, p, c, v in spec["menu"]]
        db.add_all(items)
        db.flush()
        restaurants.append((owner, r, items))

    customers = [_user(db, n, e, UserRole.CUSTOMER, p, a) for n, e, p, a in CUSTOMERS]
    partners = [_user(db, n, e, UserRole.DELIVERY_PARTNER, p) for n, e, p in PARTNERS]

    S = OrderStatus
    full = [S.ACCEPTED, S.PREPARING, S.READY, S.ASSIGNED, S.OUT_FOR_DELIVERY, S.DELIVERED]
    asha, kabir = customers
    rider, rider2 = partners
    (o1, grill, gm), (o2, green, bm), (o3, noodle, nm) = restaurants

    def actors(owner, partner):
        return {S.ACCEPTED: owner, S.PREPARING: owner, S.READY: owner, S.ASSIGNED: owner,
                S.OUT_FOR_DELIVERY: partner, S.DELIVERED: partner, S.CANCELLED: owner}

    day = 24 * 60
    delivered1 = _order(db, asha, grill, [(gm[0], 2), (gm[4], 1), (gm[6], 1)], full, 6 * day, rider, actors(o1, rider))
    delivered2 = _order(db, asha, noodle, [(nm[0], 1), (nm[4], 2)], full, 3 * day, rider2, actors(o3, rider2))
    delivered3 = _order(db, asha, grill, [(gm[2], 1), (gm[4], 1), (gm[7], 1)], full, 1 * day, rider, actors(o1, rider))
    returned = _order(db, asha, green, [(bm[0], 1), (bm[4], 1)], full, 2 * day, rider2, actors(o2, rider2))
    returned.return_status = ReturnStatus.REQUESTED
    returned.return_reason = "The smoothie was spilled and the bowl was cold on arrival."
    returned.return_requested_at = utcnow() - timedelta(days=1)
    _order(db, asha, noodle, [(nm[6], 1)], [S.CANCELLED], 4 * day, None, actors(o3, rider))
    _order(db, asha, grill, [(gm[0], 1), (gm[6], 1)], [S.ACCEPTED, S.PREPARING], 25, None, actors(o1, rider))
    _order(db, asha, grill, [(gm[5], 1)], [], 22, None, actors(o1, rider))  # stale PLACED -> reminder
    _order(db, kabir, grill, [(gm[1], 2), (gm[3], 1)], [S.ACCEPTED, S.PREPARING, S.READY, S.ASSIGNED], 40, rider,
           actors(o1, rider))
    _order(db, kabir, grill, [(gm[1], 1)], [S.ACCEPTED], 30, None, actors(o1, rider))  # stale ACCEPTED -> reminder
    _order(db, kabir, grill, [(gm[2], 1), (gm[6], 2)], [S.ACCEPTED, S.PREPARING, S.READY], 12, None, actors(o1, rider))
    _order(db, kabir, noodle, [(nm[1], 1), (nm[5], 1)], full, 2 * day, rider, actors(o3, rider))

    db.add_all([
        Review(order_id=delivered1.id, customer_id=asha.id, restaurant_id=grill.id, rating=5,
               comment="Burgers were hot and fresh. Super quick delivery!", created_at=utcnow() - timedelta(days=5)),
        Review(order_id=delivered2.id, customer_id=asha.id, restaurant_id=noodle.id, rating=4,
               comment="Tasty momos, noodles could be spicier."),
    ])
    db.commit()
    logger.info("Demo data ready. Log in with any demo email and password '%s'", DEMO_PASSWORD)
    return True


if __name__ == "__main__":
    from .database import SessionLocal, init_db

    logging.basicConfig(level=logging.INFO)
    init_db()
    with SessionLocal() as session:
        print("Seeded." if seed_demo_data(session) else "Database already has users - skipped.")
