"""AI-powered order insights for customers."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import utcnow
from ..schemas import AIInsightRequest, AIInsightResponse
from ..security import CustomerUser
from ..services import ai_insights

router = APIRouter(prefix="/ai", tags=["AI Insights"])


@router.get("/stats")
def order_stats(customer: CustomerUser, db: Session = Depends(get_db)) -> dict:
    """Locally computed spending/order statistics (no OpenAI call). Always available."""
    return ai_insights.compute_stats(ai_insights.fetch_customer_orders(db, customer.id))


@router.post("/insights", response_model=AIInsightResponse)
def order_insights(payload: AIInsightRequest, customer: CustomerUser, db: Session = Depends(get_db)):
    """Summarize or answer a question about the *authenticated* customer's order history.

    The customer id comes from the JWT, never from the request body, so one customer can never
    obtain another customer's order data through this endpoint."""
    ai_insights.rate_limiter.check(customer.id, settings.ai_rate_limit_per_minute)
    question = ai_insights.SUMMARY_PROMPT if payload.mode == "summary" else payload.question.strip()

    orders = ai_insights.fetch_customer_orders(db, customer.id)
    if not orders:
        answer = "You haven't placed any orders yet, so there is nothing to analyse. Place your first order and come back!"
        return AIInsightResponse(mode=payload.mode, question=question, answer=answer, model="none",
                                 orders_considered=0, generated_at=utcnow())

    context = ai_insights.build_context(orders)
    answer = ai_insights.ask_openai(question, context)
    return AIInsightResponse(mode=payload.mode, question=question, answer=answer, model=settings.openai_model,
                             orders_considered=context["orders_included"], generated_at=utcnow())
