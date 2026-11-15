"""Background job: remind restaurant owners about orders stuck in PLACED/ACCEPTED."""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import Order, OrderStatus, ReminderLog, utcnow

logger = logging.getLogger("campusbite.reminders")

STALE_STATUSES = (OrderStatus.PLACED, OrderStatus.ACCEPTED)


def scan_stale_orders(db: Session, restaurant_id: int | None = None) -> int:
    """Create one reminder per stale order/status (no duplicates while unresolved). Returns count created."""
    now = utcnow()
    cutoff = now - timedelta(minutes=settings.reminder_threshold_minutes)
    stmt = select(Order).where(Order.status.in_(STALE_STATUSES), Order.status_updated_at <= cutoff)
    if restaurant_id is not None:
        stmt = stmt.where(Order.restaurant_id == restaurant_id)

    created = 0
    for order in db.scalars(stmt).all():
        already = db.scalar(
            select(ReminderLog.id).where(
                ReminderLog.order_id == order.id,
                ReminderLog.order_status == order.status,
                ReminderLog.is_resolved.is_(False),
            )
        )
        if already:
            continue
        minutes = int((now - order.status_updated_at).total_seconds() // 60)
        db.add(ReminderLog(
            order_id=order.id,
            restaurant_id=order.restaurant_id,
            order_status=order.status,
            minutes_pending=minutes,
            message=f"Order #{order.id} has been {order.status.value} for {minutes} minutes without an update.",
        ))
        created += 1
    db.commit()
    return created


def run_scan(restaurant_id: int | None = None) -> int:
    """Run a scan with its own session (used by the scheduler and FastAPI BackgroundTasks)."""
    with SessionLocal() as db:
        created = scan_stale_orders(db, restaurant_id)
    if created:
        logger.info("Reminder scan created %s reminder(s)", created)
    return created


async def reminder_loop(stop_event: asyncio.Event) -> None:
    interval = settings.reminder_scan_interval_seconds
    logger.info("Reminder scheduler started (every %ss, threshold %s min)", interval, settings.reminder_threshold_minutes)
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(run_scan)
        except Exception:  # keep the loop alive no matter what
            logger.exception("Reminder scan failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            pass
    logger.info("Reminder scheduler stopped")
