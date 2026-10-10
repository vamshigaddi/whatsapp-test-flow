"""Appointment Management for Diyama Jewellers."""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel

class Appointment(BaseModel):
    booking_id: str
    phone_number: str
    customer_name: Optional[str] = "Valued Customer"
    customer_email: Optional[str] = None
    appointment_type: str  # "In-Studio VIP Visit" or "Virtual Consultation (Google Meet)"
    day: str
    time_slot: str
    interested_product: Optional[str] = None
    meet_url: Optional[str] = None
    created_at: str
    status: str = "CONFIRMED"

from app.config import settings

# In-memory storage for bookings during demo runtime
BOOKINGS_DB: Dict[str, Appointment] = {}

def generate_booking_id() -> str:
    prefix = "AURA" if settings.is_skincare_mode else "DIY"
    digits = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{digits}"

def get_available_days() -> List[str]:
    today = datetime.now()
    days = [
        "Today (" + today.strftime("%d %b") + ")",
        "Tomorrow (" + (today + timedelta(days=1)).strftime("%d %b") + ")",
        "This Weekend (Saturday)",
    ]
    return days

def get_available_slots() -> List[str]:
    return [
        "11:30 AM (Morning)",
        "03:00 PM (Afternoon)",
        "06:00 PM (Evening Consult)",
    ]

def create_appointment(
    phone_number: str,
    appointment_type: str,
    day: str,
    time_slot: str,
    customer_email: Optional[str] = None,
    interested_product: Optional[str] = None,
    base_meet_url: Optional[str] = None
) -> Appointment:
    booking_id = generate_booking_id()
    
    # Generate unique Google Meet URL slug if virtual
    meet_url = None
    if "Virtual" in appointment_type or "Meet" in appointment_type:
        prefix = "aura" if settings.is_skincare_mode else "diy"
        meet_code = f"{prefix}-{''.join(random.choices(string.ascii_lowercase, k=4))}-{''.join(random.choices(string.ascii_lowercase, k=3))}"
        meet_url = f"https://meet.google.com/{meet_code}"

    appt = Appointment(
        booking_id=booking_id,
        phone_number=phone_number,
        appointment_type=appointment_type,
        customer_email=customer_email,
        day=day,
        time_slot=time_slot,
        interested_product=interested_product,
        meet_url=meet_url,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status="CONFIRMED"
    )

    BOOKINGS_DB[booking_id] = appt
    return appt
