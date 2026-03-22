import os
import uuid
import hmac
import hashlib
from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User, Transaction
from app.auth import get_current_user
from app.dependencies import templates
import razorpay

router = APIRouter(prefix="/billing", tags=["billing"])

# Initialize Razorpay Client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "dummy_secret")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Pricing Packages (Credits : Price in INR)
PACKAGES = {
    "basic": {"credits": 5, "price_inr": 499},
    "pro": {"credits": 15, "price_inr": 1299},
    "premium": {"credits": 50, "price_inr": 3499}
}



@router.post("/create-order")
def create_order(request: Request, package_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")

    package = PACKAGES[package_id]
    amount_in_paise = package["price_inr"] * 100

    try:
        # Create Order in Razorpay
        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_{user.id[:8]}_{uuid.uuid4().hex[:8]}"
        }
        # In a real app we'd uncomment this when valid keys are provided:
        # razorpay_order = razorpay_client.order.create(data=order_data)
        # Mocking for now if key is dummy
        if "dummy" in RAZORPAY_KEY_ID:
            razorpay_order = {"id": f"order_dummy_{uuid.uuid4().hex[:8]}", "amount": amount_in_paise}
        else:
            razorpay_order = razorpay_client.order.create(data=order_data)

        # Create Transaction record
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user.id,
            amount=amount_in_paise,
            credits_added=package["credits"],
            razorpay_order_id=razorpay_order["id"],
            status="created"
        )
        db.add(transaction)
        db.commit()

        return JSONResponse(content={
            "order_id": razorpay_order["id"],
            "amount": amount_in_paise,
            "currency": "INR",
            "prefill": {
                "name": user.username,
                "email": user.email
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-payment")
async def verify_payment(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")

    transaction = db.query(Transaction).filter(Transaction.razorpay_order_id == razorpay_order_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if "dummy" not in RAZORPAY_KEY_ID:
        try:
            # Verify Signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            transaction.status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail="Signature verification failed")
            
    # Success
    transaction.status = "paid"
    transaction.razorpay_payment_id = razorpay_payment_id
    transaction.razorpay_signature = razorpay_signature
    
    # Add credits to user
    user = db.query(User).filter(User.id == transaction.user_id).first()
    user.credits += transaction.credits_added
    
    db.commit()
    
    return JSONResponse(content={"status": "success", "new_credits": user.credits})
