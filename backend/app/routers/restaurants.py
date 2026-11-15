"""Public browsing endpoints: restaurants, menus, dish search, reviews."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import MenuItem, Restaurant, Review
from ..schemas import DishSearchOut, MenuItemOut, Page, PublicReviewOut, RestaurantOut, ReviewOut
from ..utils import PageParams, page_params, paginate

router = APIRouter(tags=["Restaurants & Menus"])

SortOption = Literal["name", "price_asc", "price_desc", "newest"]


def ratings_for(db: Session, restaurant_ids: list[int]) -> dict[int, tuple[float | None, int]]:
    if not restaurant_ids:
        return {}
    rows = db.execute(
        select(Review.restaurant_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.restaurant_id.in_(restaurant_ids))
        .group_by(Review.restaurant_id)
    ).all()
    return {rid: (round(float(avg), 2) if avg is not None else None, cnt) for rid, avg, cnt in rows}


def restaurant_out(r: Restaurant, ratings: dict) -> RestaurantOut:
    avg, cnt = ratings.get(r.id, (None, 0))
    return RestaurantOut.model_validate(r).model_copy(update={"avg_rating": avg, "review_count": cnt})


def _apply_menu_filters(stmt, q, min_price, max_price, category, available_only, sort):
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(MenuItem.name.ilike(like), MenuItem.description.ilike(like)))
    if min_price is not None:
        stmt = stmt.where(MenuItem.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(MenuItem.price <= max_price)
    if category:
        stmt = stmt.where(MenuItem.category == category)
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    order = {
        "name": (MenuItem.name.asc(),),
        "price_asc": (MenuItem.price.asc(), MenuItem.name.asc()),
        "price_desc": (MenuItem.price.desc(), MenuItem.name.asc()),
        "newest": (MenuItem.created_at.desc(),),
    }[sort]
    return stmt.order_by(*order, MenuItem.id)


def _check_price_range(min_price, max_price):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "min_price cannot be greater than max_price")


@router.get("/restaurants", response_model=Page[RestaurantOut])
def list_restaurants(
    q: str | None = Query(None, max_length=100, description="Search by restaurant name or cuisine"),
    cuisine: str | None = Query(None, max_length=80),
    open_only: bool = False,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    stmt = select(Restaurant)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Restaurant.name.ilike(like), Restaurant.cuisine.ilike(like)))
    if cuisine:
        stmt = stmt.where(Restaurant.cuisine.ilike(cuisine))
    if open_only:
        stmt = stmt.where(Restaurant.is_open.is_(True))
    stmt = stmt.order_by(Restaurant.is_open.desc(), Restaurant.name, Restaurant.id)
    items, total = paginate(db, stmt, params)
    ratings = ratings_for(db, [r.id for r in items])
    return Page.build([restaurant_out(r, ratings) for r in items], total, params.page, params.page_size)


@router.get("/restaurants/cuisines", response_model=list[str])
def list_cuisines(db: Session = Depends(get_db)):
    rows = db.scalars(select(Restaurant.cuisine).where(Restaurant.cuisine.is_not(None)).distinct()).all()
    return sorted({c for c in rows if c})


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    r = db.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return restaurant_out(r, ratings_for(db, [r.id]))


@router.get("/restaurants/{restaurant_id}/menu", response_model=Page[MenuItemOut])
def restaurant_menu(
    restaurant_id: int,
    q: str | None = Query(None, max_length=100, description="Search dishes by name/description"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    category: str | None = Query(None, max_length=80),
    available_only: bool = False,
    sort: SortOption = "name",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not db.get(Restaurant, restaurant_id):
        raise HTTPException(404, "Restaurant not found")
    _check_price_range(min_price, max_price)
    stmt = _apply_menu_filters(select(MenuItem).where(MenuItem.restaurant_id == restaurant_id),
                               q, min_price, max_price, category, available_only, sort)
    params = PageParams(page, page_size)
    items, total = paginate(db, stmt, params)
    return Page.build(items, total, page, page_size)


@router.get("/restaurants/{restaurant_id}/categories", response_model=list[str])
def restaurant_categories(restaurant_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(MenuItem.category).where(MenuItem.restaurant_id == restaurant_id).distinct()).all()
    return sorted({c for c in rows if c})


@router.get("/restaurants/{restaurant_id}/reviews", response_model=Page[PublicReviewOut])
def restaurant_reviews(restaurant_id: int, params: PageParams = Depends(page_params), db: Session = Depends(get_db)):
    if not db.get(Restaurant, restaurant_id):
        raise HTTPException(404, "Restaurant not found")
    stmt = select(Review).where(Review.restaurant_id == restaurant_id).order_by(Review.created_at.desc())
    items, total = paginate(db, stmt, params, options=[selectinload(Review.customer)])
    out = [
        PublicReviewOut.model_validate({**ReviewOut.model_validate(r).model_dump(), "customer_name": r.customer.name.split(" ")[0]})
        for r in items
    ]
    return Page.build(out, total, params.page, params.page_size)


@router.get("/dishes", response_model=Page[DishSearchOut])
def search_dishes(
    q: str | None = Query(None, max_length=100),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    available_only: bool = True,
    sort: SortOption = "price_asc",
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    """Search dishes across all restaurants by name and price range."""
    _check_price_range(min_price, max_price)
    stmt = _apply_menu_filters(select(MenuItem), q, min_price, max_price, None, available_only, sort)
    items, total = paginate(db, stmt, params, options=[selectinload(MenuItem.restaurant)])
    out = [DishSearchOut.model_validate({**MenuItemOut.model_validate(m).model_dump(), "restaurant_name": m.restaurant.name})
           for m in items]
    return Page.build(out, total, params.page, params.page_size)
