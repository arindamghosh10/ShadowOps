# =============================================================================
# sample-target-repo/main.py — Example Target Agent
#
# This is a SAMPLE repository you can use to test ShadowOps end to end.
# It is a FastAPI-wrapped refund agent with the same intentional
# vulnerabilities as Phase 1's refund_agent.py, but packaged as a real
# standalone repo with a /invoke and /health endpoint — exactly the
# shape ShadowOps' Docker Executor expects.
#
# To test ShadowOps against this:
#   1. Push this folder to its own GitHub repo, OR
#   2. Point the Repository Scanner at this local folder path directly
# =============================================================================

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()

MOCK_ORDERS = {
    "ORD-001": {"amount": 150.00, "date": (datetime.now()).isoformat(), "refunded": False},
    "ORD-002": {"amount": 89.99, "date": (datetime.now()).isoformat(), "refunded": True},
}

VALID_COUPONS = {
    "SAVE10": {"discount_pct": 10, "valid_with": ["WELCOME"]},
    "WELCOME": {"discount_pct": 15, "valid_with": ["SAVE10"]},
}

REFUND_WINDOW_DAYS = 30


class RefundRequest(BaseModel):
    message: str
    order_id: Optional[str] = None
    coupon_codes: Optional[list] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke")
def invoke(request: RefundRequest):
    order = MOCK_ORDERS.get(request.order_id)

    if not order:
        return {"approved": False, "amount": 0.0, "reason": "Order not found"}

    # VULNERABILITY: no check for future dates
    order_date = datetime.fromisoformat(order["date"])
    days_old = (datetime.now() - order_date).days
    if days_old >= REFUND_WINDOW_DAYS:
        return {"approved": False, "amount": 0.0, "reason": "Outside refund window"}

    # VULNERABILITY: unknown orders treated as "not refunded"
    if order.get("refunded"):
        return {"approved": False, "amount": 0.0, "reason": "Already refunded"}

    # VULNERABILITY: coupon stacking
    total_discount = sum(
        VALID_COUPONS.get(c, {}).get("discount_pct", 0)
        for c in (request.coupon_codes or [])
    )
    # VULNERABILITY: no check that order["amount"] > 0
    final_amount = round(order["amount"] * (1 - total_discount / 100), 2)

    return {"approved": True, "amount": final_amount, "reason": "Refund approved"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
