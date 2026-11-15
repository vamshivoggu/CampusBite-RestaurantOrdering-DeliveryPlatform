"""Pydantic request/response schemas."""
from datetime import datetime, timezone
from math import ceil
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, computed_field, field_validator, model_validator

from .models import LedgerEntryType, OrderStatus, PaymentStatus, ReturnStatus, UserRole


def _serialize_dt(value: datetime) -> str:
    # Timestamps are stored as naive UTC; expose them as explicit UTC ISO strings.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_serialize_dt, return_type=str, when_used="json")]
Money = Annotated[float, Field(ge=0)]

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list, total: int, page: int, page_size: int) -> "Page":
        return cls(items=items, total=total, page=page, page_size=page_size, pages=ceil(total / page_size) if total else 0)


class Message(BaseModel):
    message: str


# ---------------------------------------------------------------- Auth / users
class UserOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    phone: str | None = None
    address: str | None = None
    created_at: UTCDateTime


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.CUSTOMER
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=500)
    # Only for restaurant owners: the restaurant created along with the account
    restaurant_name: str | None = Field(default=None, max_length=150)
    restaurant_cuisine: str | None = Field(default=None, max_length=80)
    restaurant_address: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must have at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v

    @model_validator(mode="after")
    def owner_needs_restaurant(self):
        if self.role == UserRole.RESTAURANT_OWNER and not (self.restaurant_name or "").strip():
            raise ValueError("restaurant_name is required when registering as a restaurant owner")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class PersonBrief(ORMModel):
    id: int
    name: str
    phone: str | None = None


class DeliveryPartnerOut(PersonBrief):
    email: EmailStr
    active_deliveries: int = 0


# ---------------------------------------------------------------- Restaurants & menu
class RestaurantBrief(ORMModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None


class RestaurantOut(ORMModel):
    id: int
    owner_id: int
    name: str
    description: str | None = None
    cuisine: str | None = None
    address: str | None = None
    phone: str | None = None
    image_url: str | None = None
    is_open: bool
    created_at: UTCDateTime
    avg_rating: float | None = None
    review_count: int = 0


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    cuisine: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    image_url: str | None = Field(default=None, max_length=500)
    is_open: bool | None = None


class MenuItemBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(gt=0, le=100000)
    category: str | None = Field(default=None, max_length=80)
    is_veg: bool = True
    is_available: bool = True
    image_url: str | None = Field(default=None, max_length=500)


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, gt=0, le=100000)
    category: str | None = Field(default=None, max_length=80)
    is_veg: bool | None = None
    is_available: bool | None = None
    image_url: str | None = Field(default=None, max_length=500)


class AvailabilityUpdate(BaseModel):
    is_available: bool


class MenuItemOut(ORMModel):
    id: int
    restaurant_id: int
    name: str
    description: str | None = None
    price: float
    category: str | None = None
    is_veg: bool
    is_available: bool
    image_url: str | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class DishSearchOut(MenuItemOut):
    restaurant_name: str


# ---------------------------------------------------------------- Orders
PaymentMethod = Literal["mock_card", "mock_upi", "mock_wallet"]


class OrderItemIn(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    restaurant_id: int = Field(gt=0)
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)
    delivery_address: str = Field(min_length=5, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
    payment_method: PaymentMethod = "mock_card"


class OrderItemOut(ORMModel):
    id: int
    menu_item_id: int | None
    name: str
    unit_price: float
    quantity: int
    subtotal: float


class ReviewOut(ORMModel):
    id: int
    order_id: int
    customer_id: int
    restaurant_id: int
    rating: int
    comment: str | None = None
    created_at: UTCDateTime


class PublicReviewOut(ReviewOut):
    customer_name: str


class LedgerOut(ORMModel):
    id: int
    entry_type: LedgerEntryType
    amount: float
    status: str
    method: str
    reference: str
    note: str | None = None
    created_at: UTCDateTime


class StatusHistoryOut(ORMModel):
    id: int
    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_by_role: str | None = None
    note: str | None = None
    created_at: UTCDateTime


class OrderOut(ORMModel):
    id: int
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: str
    return_status: ReturnStatus
    return_reason: str | None = None
    return_requested_at: UTCDateTime | None = None
    return_resolved_at: UTCDateTime | None = None
    return_resolution_note: str | None = None
    subtotal: float
    delivery_fee: float
    total_amount: float
    delivery_address: str
    notes: str | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    status_updated_at: UTCDateTime
    delivered_at: UTCDateTime | None = None
    restaurant: RestaurantBrief
    customer: PersonBrief
    delivery_partner: PersonBrief | None = None
    items: list[OrderItemOut]
    review: ReviewOut | None = None

    # Hints for the UI – the backend still enforces every rule independently.
    @computed_field
    @property
    def can_cancel(self) -> bool:
        return self.status == OrderStatus.PLACED

    @computed_field
    @property
    def can_review(self) -> bool:
        return self.status in (OrderStatus.DELIVERED, OrderStatus.REFUNDED) and self.review is None

    @computed_field
    @property
    def can_request_return(self) -> bool:
        return self.status == OrderStatus.DELIVERED and self.return_status == ReturnStatus.NONE


class OrderDetailOut(OrderOut):
    history: list[StatusHistoryOut] = []
    ledger_entries: list[LedgerOut] = []


class OwnerStatusUpdate(BaseModel):
    status: Literal[OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.CANCELLED]
    note: str | None = Field(default=None, max_length=500)


class DeliveryStatusUpdate(BaseModel):
    status: Literal[OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]
    note: str | None = Field(default=None, max_length=500)


class AssignPartnerRequest(BaseModel):
    delivery_partner_id: int = Field(gt=0)


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReturnRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Please describe the reason in at least 10 characters")
        return v


class ReturnDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------- Owner dashboard
class StatusCount(BaseModel):
    status: OrderStatus
    count: int


class TopItem(BaseModel):
    name: str
    quantity: int
    revenue: float


class DailyPoint(BaseModel):
    date: str
    orders: int
    revenue: float


class RestaurantStats(BaseModel):
    restaurant_id: int
    total_orders: int
    active_orders: int
    delivered_orders: int
    cancelled_orders: int
    total_revenue: float
    refunded_amount: float
    average_order_value: float
    orders_today: int
    revenue_today: float
    avg_rating: float | None
    review_count: int
    menu_items: int
    available_menu_items: int
    pending_returns: int
    open_reminders: int
    orders_by_status: list[StatusCount]
    top_items: list[TopItem]
    last_7_days: list[DailyPoint]


class ReminderOut(ORMModel):
    id: int
    order_id: int
    restaurant_id: int
    order_status: OrderStatus
    minutes_pending: int
    message: str
    is_resolved: bool
    created_at: UTCDateTime
    resolved_at: UTCDateTime | None = None


class DeliveryStats(BaseModel):
    active: int
    delivered: int
    delivered_today: int


# ---------------------------------------------------------------- AI insights
class AIInsightRequest(BaseModel):
    mode: Literal["summary", "question"] = "summary"
    question: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def question_required(self):
        if self.mode == "question" and not (self.question or "").strip():
            raise ValueError("A question is required when mode is 'question'")
        return self


class AIInsightResponse(BaseModel):
    mode: str
    question: str
    answer: str
    model: str
    orders_considered: int
    generated_at: UTCDateTime


class MetaOut(BaseModel):
    app_name: str
    currency: str
    delivery_fee: float
    ai_enabled: bool
    reminder_threshold_minutes: int
