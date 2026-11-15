"""Shared helpers: pagination and common order filters."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from .models import Order, OrderStatus


@dataclass
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def paginate(db: Session, stmt: Select, params: PageParams, options: list | None = None) -> tuple[list, int]:
    """Count the filtered statement, then fetch one page (loader options applied only to the page query)."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    page_stmt = stmt.limit(params.page_size).offset(params.offset)
    if options:
        page_stmt = page_stmt.options(*options)
    return list(db.scalars(page_stmt).unique().all()), total


@dataclass
class OrderFilters:
    status: list[OrderStatus] | None
    date_from: date | None
    date_to: date | None


def order_filters(
    status: list[OrderStatus] | None = Query(None, description="Filter by one or more statuses"),
    date_from: date | None = Query(None, description="Orders created on/after this date (YYYY-MM-DD, UTC)"),
    date_to: date | None = Query(None, description="Orders created on/before this date (YYYY-MM-DD, UTC)"),
) -> OrderFilters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be on or before date_to")
    return OrderFilters(status=status, date_from=date_from, date_to=date_to)


def apply_order_filters(stmt: Select, f: OrderFilters) -> Select:
    if f.status:
        stmt = stmt.where(Order.status.in_(f.status))
    if f.date_from:
        stmt = stmt.where(Order.created_at >= datetime.combine(f.date_from, time.min))
    if f.date_to:
        stmt = stmt.where(Order.created_at < datetime.combine(f.date_to + timedelta(days=1), time.min))
    return stmt
