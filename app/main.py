"""FastAPI Application for Diyama Jewellers WhatsApp Bot."""

import io
import csv
import logging
import urllib.parse
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, Response, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.catalog_data import PRODUCTS, get_product
from app.clinic_data import CLINIC_TREATMENTS
from app.appointments import BOOKINGS_DB
from app.bot_router import handle_incoming_message, send_main_menu, show_rings_submenu

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Diyama Jewellers WhatsApp API",
    description="WhatsApp Catalogue, Jewellery Browsing, and Appointment Booking System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health and status dashboard."""
    return {
        "brand": "Diyama Jewellers",
        "status": "online",
        "meta_configured": settings.is_meta_configured,
        "phone_number_id": settings.PHONE_NUMBER_ID if settings.PHONE_NUMBER_ID else "Not configured yet",
        "webhook_endpoint": "/webhook",
        "active_appointments": len(BOOKINGS_DB),
        "total_catalog_items": len(PRODUCTS),
        "commerce_catalog_id": settings.META_CATALOG_ID or "Optional (Interactive cards active)"
    }


# ===========================================================================
# META WHATSAPP WEBHOOK VERIFICATION (GET) & EVENT INGESTION (POST)
# ===========================================================================

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Webhook verification handshake with Meta Cloud API.
    Meta sends: hub.mode=subscribe, hub.verify_token=..., hub.challenge=...
    """
    logger.info("Webhook verification request: mode=%s, token=%s", hub_mode, hub_verify_token)

    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook successfully verified by Meta!")
        # Challenge must be returned as integer/raw text
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Webhook verification failed: token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming WhatsApp message events from Meta.
    Always returns HTTP 200 OK swiftly to acknowledge Meta's delivery.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"status": "invalid_json"}, status_code=400)

    # Validate that this is a whatsapp business account notification
    if body.get("object") != "whatsapp_business_account":
        return JSONResponse(content={"status": "ignored"}, status_code=200)

    entries: List[Dict[str, Any]] = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Extract messages list
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            sender_name = None
            if contacts:
                profile = contacts[0].get("profile", {})
                sender_name = profile.get("name")

            for msg in messages:
                # Process message asynchronously in background task so webhook responds <200ms
                background_tasks.add_task(handle_incoming_message, msg, sender_name)

    return JSONResponse(content={"status": "EVENT_RECEIVED"}, status_code=200)


# ===========================================================================
# COMMERCE CATALOG EXPORTS & APPOINTMENT APIS
# ===========================================================================

@app.get("/catalog")
async def get_catalog():
    """Returns all available jewelry pieces in JSON."""
    return {
        "brand": "Diyama Jewellers",
        "products": list(PRODUCTS.values())
    }


@app.get("/catalog/meta-feed.csv")
async def export_meta_commerce_csv():
    """
    Exports products in standard Meta Commerce Manager Product Feed CSV format.
    You can directly import this CSV into Meta Commerce Manager -> Catalog -> Data Sources!
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Standard Meta Product Catalog Columns
    writer.writerow([
        "id",
        "title",
        "description",
        "availability",
        "condition",
        "price",
        "link",
        "image_link",
        "brand",
        "google_product_category"
    ])

    for p in PRODUCTS.values():
        writer.writerow([
            p.retailer_id,
            p.title,
            f"{p.description} Metal: {p.gold_metal}. Diamond: {p.diamond_specs}. Certification: {p.certification}",
            "in stock",
            "new",
            f"{int(p.price_amount)} INR",
            settings.GOOGLE_MAPS_LINK,
            p.image_url,
            settings.STORE_NAME,
            "Apparel & Accessories > Jewelry > Rings"
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=diyama_jewellers_catalog.csv"}
    )


@app.get("/appointments")
async def list_appointments():
    """Lists all booked appointments in runtime memory."""
    return {
        "total": len(BOOKINGS_DB),
        "appointments": list(BOOKINGS_DB.values())
    }


# ===========================================================================
# SIMULATOR / TEST ENDPOINTS (To demo or test without waiting for Meta)
# ===========================================================================

@app.post("/test-simulate")
async def test_simulate(phone: str = Query("919876543210"), action: str = Query("hi")):
    """
    Simulates sending an incoming message to the bot locally for testing.
    Useful for testing console logs and flow logic without a live phone.
    """
    msg = {
        "from": phone,
        "type": "text",
        "text": {"body": action}
    }
    await handle_incoming_message(msg, sender_name="Test Customer")
    return {"message": f"Simulated message '{action}' processed for {phone}"}


@app.get("/lookbook", response_class=HTMLResponse)
async def view_lookbook(mode: Optional[str] = Query(None), phone: Optional[str] = Query(None)):
    """Renders digital showcase with interactive WhatsApp action buttons."""
    redirect_phone = "".join(c for c in phone if c.isdigit()) if phone else settings.WHATSAPP_REDIRECT_PHONE
    if not redirect_phone:
        redirect_phone = "15556502265"

    is_skin = (mode.lower() == "skincare") if mode else settings.is_skincare_mode

    if is_skin:
        store_name = settings.STORE_NAME if settings.is_skincare_mode else "Aura Skin & Aesthetics Clinic"
        store_address = settings.STORE_ADDRESS if settings.is_skincare_mode else "Aura Aesthetics Clinic, Road No. 36, Jubilee Hills, Hyderabad"
        store_hours = settings.STORE_HOURS if settings.is_skincare_mode else "Mon - Sat: 10:00 AM - 8:00 PM (Sunday by Appt)"
        general_chat = urllib.parse.quote(f"Hi {store_name}, I am browsing your clinical aesthetics menu and have a question.")
        general_book = urllib.parse.quote(f"Hi {store_name}, I would like to book a doctor consultation.")
        cards_html = ""
        for t in CLINIC_TREATMENTS.values():
            enquire_msg = urllib.parse.quote(f"Hi {store_name}, I would like to enquire about {t.title} ({t.retailer_id})")
            book_msg = urllib.parse.quote(f"Hi {store_name}, I would like to book a doctor consultation for {t.title} ({t.retailer_id})")
            cards_html += f"""
            <div class="card">
                <div class="img-wrap">
                    <img src="{t.image_url}" alt="{t.title}" loading="lazy" />
                    <span class="badge">{t.category}</span>
                </div>
                <div class="card-body">
                    <div class="sku">{t.retailer_id}</div>
                    <h3>{t.title}</h3>
                    <div class="specs">
                        <div><strong>Duration:</strong> {t.duration}</div>
                        <div><strong>Specialist:</strong> {t.doctor}</div>
                        <div><strong>Key Benefits:</strong> {t.benefits}</div>
                    </div>
                    <div class="price">{t.price_formatted}</div>
                    <p class="desc">{t.description}</p>
                    <div class="card-actions">
                        <a class="btn-action btn-enquire" href="https://wa.me/{redirect_phone}?text={enquire_msg}" target="_blank">
                            💬 Enquire
                        </a>
                        <a class="btn-action btn-book" href="https://wa.me/{redirect_phone}?text={book_msg}" target="_blank">
                            📅 Book Doctor
                        </a>
                    </div>
                </div>
            </div>
            """
        page_title = f"{store_name} • Aesthetic Dermatology Showcase"
        subtitle = "Medical Aesthetics & Advanced Dermatology • Jubilee Hills"
        tag_badge = "✨ CLINICAL TREATMENT MENU"
    else:
        store_name = settings.STORE_NAME if not settings.is_skincare_mode else "Diyama Jewellers"
        store_address = settings.STORE_ADDRESS if not settings.is_skincare_mode else "Diyama Jewellers- Premium Lab Grown Diamond Jewellery in Banjara hills"
        store_hours = settings.STORE_HOURS if not settings.is_skincare_mode else "Mon - Sun: 10:30 AM - 8:30 PM"
        general_chat = urllib.parse.quote(f"Hi {store_name}, I am browsing your jewellery collection and have a question.")
        general_book = urllib.parse.quote(f"Hi {store_name}, I would like to book a VIP studio viewing.")
        cards_html = ""
        for p in PRODUCTS.values():
            enquire_msg = urllib.parse.quote(f"Hi {store_name}, I would like to enquire about {p.title} ({p.retailer_id})")
            book_msg = urllib.parse.quote(f"Hi {store_name}, I would like to book an appointment to view {p.title} ({p.retailer_id})")
            cards_html += f"""
            <div class="card">
                <div class="img-wrap">
                    <img src="{p.image_url}" alt="{p.title}" loading="lazy" />
                    <span class="badge">{p.category}</span>
                </div>
                <div class="card-body">
                    <div class="sku">{p.retailer_id}</div>
                    <h3>{p.title}</h3>
                    <div class="specs">
                        <div><strong>Metal:</strong> {p.gold_metal}</div>
                        <div><strong>Diamonds:</strong> {p.diamond_specs}</div>
                        <div><strong>Certificate:</strong> {p.certification}</div>
                    </div>
                    <div class="price">{p.price_formatted}</div>
                    <p class="desc">{p.description}</p>
                    <div class="card-actions">
                        <a class="btn-action btn-enquire" href="https://wa.me/{redirect_phone}?text={enquire_msg}" target="_blank">
                            💬 Enquire
                        </a>
                        <a class="btn-action btn-book" href="https://wa.me/{redirect_phone}?text={book_msg}" target="_blank">
                            📅 Book Viewing
                        </a>
                    </div>
                </div>
            </div>
            """
        page_title = f"{store_name} • Haute Joaillerie Showcase"
        subtitle = "Haute Joaillerie & Lab-Grown Diamonds • Flagship Studio"
        tag_badge = "💎 EXCLUSIVE FINE JEWELLERY"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{page_title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0b0c10;
                --surface: #13161f;
                --surface-hover: #191e2b;
                --border: #232838;
                --gold: #dfba73;
                --gold-light: #f4d99b;
                --text: #f0f2f5;
                --muted: #9aa1b0;
                --wa-green: #25D366;
                --wa-dark: #128C7E;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Montserrat', sans-serif;
                padding-bottom: 80px;
                line-height: 1.5;
            }}
            header {{
                text-align: center;
                padding: 50px 20px 30px;
                border-bottom: 1px solid var(--border);
                background: radial-gradient(circle at 50% 0%, rgba(223,186,115,0.12) 0%, rgba(11,12,16,0) 70%);
            }}
            .tag-badge {{
                display: inline-block;
                padding: 5px 14px;
                border-radius: 20px;
                background: rgba(223,186,115,0.1);
                border: 1px solid rgba(223,186,115,0.3);
                color: var(--gold);
                font-size: 0.75rem;
                font-weight: 600;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 12px;
            }}
            h1 {{
                font-family: 'Cinzel', serif;
                font-size: 2.3rem;
                letter-spacing: 3px;
                color: var(--gold);
                margin-bottom: 8px;
            }}
            .subtitle {{
                font-size: 0.92rem;
                color: var(--muted);
                letter-spacing: 1px;
                text-transform: uppercase;
                margin-bottom: 24px;
            }}
            .header-actions {{
                display: flex;
                justify-content: center;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 10px;
            }}
            .hdr-btn {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 11px 22px;
                border-radius: 30px;
                text-decoration: none;
                font-size: 0.88rem;
                font-weight: 600;
                transition: all 0.25s ease;
            }}
            .hdr-chat {{
                background: rgba(255, 255, 255, 0.05);
                color: var(--text);
                border: 1px solid var(--border);
            }}
            .hdr-chat:hover {{
                background: rgba(255, 255, 255, 0.1);
                border-color: var(--gold);
                color: #fff;
            }}
            .hdr-book {{
                background: linear-gradient(135deg, var(--gold) 0%, #b89146 100%);
                color: #0b0c10;
                border: 1px solid var(--gold);
                box-shadow: 0 4px 15px rgba(223,186,115,0.25);
            }}
            .hdr-book:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(223,186,115,0.4);
            }}
            .container {{
                max-width: 1160px;
                margin: 40px auto;
                padding: 0 20px;
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 28px;
            }}
            .card {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 14px;
                overflow: hidden;
                transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
                display: flex;
                flex-direction: column;
            }}
            .card:hover {{
                transform: translateY(-5px);
                border-color: rgba(223,186,115,0.6);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            }}
            .img-wrap {{
                position: relative;
                width: 100%;
                height: 250px;
                overflow: hidden;
                background: #000;
            }}
            .img-wrap img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.5s ease;
            }}
            .card:hover .img-wrap img {{
                transform: scale(1.06);
            }}
            .badge {{
                position: absolute;
                top: 14px;
                right: 14px;
                background: rgba(11, 12, 16, 0.88);
                backdrop-filter: blur(10px);
                color: var(--gold);
                padding: 5px 12px;
                font-size: 0.72rem;
                font-weight: 600;
                border-radius: 20px;
                letter-spacing: 0.5px;
                border: 1px solid rgba(223,186,115,0.5);
            }}
            .card-body {{
                padding: 22px;
                display: flex;
                flex-direction: column;
                flex-grow: 1;
            }}
            .sku {{
                font-size: 0.75rem;
                color: var(--gold);
                letter-spacing: 1.5px;
                font-weight: 600;
                text-transform: uppercase;
                margin-bottom: 6px;
            }}
            h3 {{
                font-family: 'Cinzel', serif;
                font-size: 1.18rem;
                margin-bottom: 12px;
                line-height: 1.35;
                color: #fff;
            }}
            .specs {{
                font-size: 0.83rem;
                color: var(--muted);
                line-height: 1.6;
                margin-bottom: 14px;
                border-bottom: 1px solid var(--border);
                padding-bottom: 12px;
            }}
            .specs strong {{ color: var(--text); }}
            .price {{
                font-size: 1.35rem;
                font-weight: 700;
                color: var(--gold-light);
                margin-bottom: 10px;
                letter-spacing: 0.5px;
            }}
            .desc {{
                font-size: 0.84rem;
                color: var(--muted);
                line-height: 1.55;
                margin-bottom: 20px;
                flex-grow: 1;
            }}
            .card-actions {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: auto;
            }}
            .btn-action {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                padding: 12px 10px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 0.84rem;
                font-weight: 600;
                transition: all 0.2s ease;
                cursor: pointer;
                text-align: center;
            }}
            .btn-enquire {{
                background: rgba(223, 186, 115, 0.1);
                color: var(--gold-light);
                border: 1px solid rgba(223, 186, 115, 0.45);
            }}
            .btn-enquire:hover {{
                background: rgba(223, 186, 115, 0.22);
                border-color: var(--gold);
                transform: translateY(-2px);
                color: #fff;
            }}
            .btn-book {{
                background: linear-gradient(135deg, var(--wa-green) 0%, var(--wa-dark) 100%);
                color: #fff;
                border: 1px solid var(--wa-green);
                box-shadow: 0 4px 12px rgba(37, 211, 102, 0.25);
            }}
            .btn-book:hover {{
                filter: brightness(1.1);
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(37, 211, 102, 0.4);
            }}
            .footer {{
                text-align: center;
                color: var(--muted);
                font-size: 0.88rem;
                margin-top: 40px;
                padding: 20px;
            }}
            .floating-wa {{
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                color: #ffffff;
                border-radius: 50px;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                box-shadow: 0 8px 24px rgba(37, 211, 102, 0.35);
                z-index: 999;
                transition: transform 0.25s ease, box-shadow 0.25s ease;
            }}
            .floating-wa:hover {{
                transform: scale(1.05);
                box-shadow: 0 10px 28px rgba(37, 211, 102, 0.5);
            }}
            @media (max-width: 480px) {{
                h1 {{ font-size: 1.8rem; }}
                .container {{ grid-template-columns: 1fr; }}
                .card-actions {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="tag-badge">{tag_badge}</div>
            <h1>{store_name}</h1>
            <div class="subtitle">{subtitle}</div>
            <div class="header-actions">
                <a class="hdr-btn hdr-chat" href="https://wa.me/{redirect_phone}?text={general_chat}" target="_blank">
                    💬 WhatsApp Concierge
                </a>
                <a class="hdr-btn hdr-book" href="https://wa.me/{redirect_phone}?text={general_book}" target="_blank">
                    📅 Book VIP Appointment
                </a>
            </div>
        </header>
        <div class="container">
            {cards_html}
        </div>
        <div class="footer">
            📍 {store_address}<br>🕒 {store_hours}
        </div>
        <a class="floating-wa" href="https://wa.me/{redirect_phone}?text={general_chat}" target="_blank">
            💬 Chat on WhatsApp
        </a>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


@app.get("/admin", response_class=HTMLResponse)
async def admin_portal():
    """Renders the executive staff concierge dashboard."""
    appointments = list(BOOKINGS_DB.values())
    total_appts = len(appointments)
    studio_visits = sum(1 for a in appointments if "Studio" in a.appointment_type or "Store" in a.appointment_type or "Clinic" in a.appointment_type)
    virtual_meets = sum(1 for a in appointments if "Virtual" in a.appointment_type or "Meet" in a.appointment_type)

    if settings.is_skincare_mode:
        admin_page_title = f"{settings.STORE_NAME} • VIP Patient Concierge"
        logo_icon = "✨"
        tagline = "Executive Dermatology & Aesthetics Portal • Jubilee Hills"
        btn_lookbook_text = "📖 View Treatment Guide"
        card2_label = "🏬 In-Clinic Doctor Visits"
        card2_val = total_appts
        card3_label = "👩‍⚕️ Active Dermatologists"
        card3_val = "2 On Duty"
        card4_label = "Clinical Procedures Offered"
        card4_val = len(CLINIC_TREATMENTS)
        panel_title = "Confirmed Patient Doctor Appointments"
        th_client = "Patient & Phone"
        th_product = "Procedure / Concern"
        th_mode = "Visit Type"
        in_clinic_label = "🏬 In-Clinic Visit"
        product_icon = "🩺"
    else:
        admin_page_title = f"{settings.STORE_NAME} • VIP Concierge Portal"
        logo_icon = "💎"
        tagline = "Staff VIP Concierge & Appointment Portal • Banjara Hills"
        btn_lookbook_text = "📖 View Showcase Lookbook"
        card2_label = "🏬 In-Studio VIP Lounge"
        card2_val = studio_visits
        card3_label = "💻 Virtual (Google Meet)"
        card3_val = virtual_meets
        card4_label = "Active Catalogue Pieces"
        card4_val = len(PRODUCTS)
        panel_title = "Confirmed VIP Client Appointments"
        th_client = "Client & Phone"
        th_product = "Curated Diamond Piece"
        th_mode = "Consultation Mode"
        in_clinic_label = "🏬 In-Studio"
        product_icon = "💍"

    rows_html = ""
    if not appointments:
        rows_html = """
        <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: var(--muted);">
                ✨ No appointments yet. Send a message on WhatsApp to see live bookings arrive here!
            </td>
        </tr>
        """
    else:
        for a in reversed(appointments):
            if settings.is_skincare_mode:
                meet_btn = f'<span class="badge-studio">{in_clinic_label}</span>'
            else:
                meet_btn = (
                    f'<a href="{a.meet_url}" target="_blank" class="badge-link">🔗 Join Meet</a>'
                    if a.meet_url else f'<span class="badge-studio">{in_clinic_label}</span>'
                )
            email_display = f'<span class="email-tag">{a.customer_email}</span>' if a.customer_email else '<span style="color:var(--muted); font-size:0.8rem;">Registered in clinic</span>'
            product_display = f'{product_icon} <strong>{a.interested_product}</strong>' if a.interested_product else '<span style="color:var(--muted);">General Doctor Consultation</span>'

            rows_html += f"""
            <tr>
                <td><span class="booking-ref">{a.booking_id}</span></td>
                <td>
                    <div style="font-weight:600; color:#fff;">{a.customer_name}</div>
                    <div style="font-size:0.8rem; color:var(--gold);">{a.phone_number}</div>
                </td>
                <td>{email_display}</td>
                <td>
                    <div style="font-weight:600;">{a.day}</div>
                    <div style="font-size:0.82rem; color:var(--muted);">{a.time_slot}</div>
                </td>
                <td>{product_display}</td>
                <td>{meet_btn}</td>
                <td><span class="status-badge">{a.status}</span></td>
            </tr>
            """

    admin_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{admin_page_title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #090a0d;
                --surface: #11141a;
                --surface-card: #161b22;
                --border: #232936;
                --gold: #dfba73;
                --gold-light: #f5dfac;
                --text: #eaecee;
                --muted: #858d9c;
                --green: #22c55e;
                --blue: #38bdf8;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Montserrat', sans-serif;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }}
            nav {{
                background: var(--surface);
                border-bottom: 1px solid var(--border);
                padding: 18px 30px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            .logo {{
                font-family: 'Cinzel', serif;
                font-size: 1.35rem;
                font-weight: 700;
                color: var(--gold);
                letter-spacing: 2px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .tagline {{
                font-size: 0.72rem;
                color: var(--muted);
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            .nav-actions {{
                display: flex;
                gap: 12px;
                align-items: center;
            }}
            .btn-lookbook {{
                background: transparent;
                border: 1px solid var(--gold);
                color: var(--gold);
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
                text-decoration: none;
                transition: background 0.2s;
            }}
            .btn-lookbook:hover {{
                background: rgba(223,186,115,0.12);
            }}
            .main-content {{
                max-width: 1250px;
                margin: 30px auto;
                padding: 0 25px;
                width: 100%;
                flex-grow: 1;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 20px;
                margin-bottom: 35px;
            }}
            .stat-card {{
                background: var(--surface-card);
                border: 1px solid var(--border);
                border-radius: 10px;
                padding: 22px;
                display: flex;
                flex-direction: column;
            }}
            .stat-label {{
                font-size: 0.78rem;
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            .stat-val {{
                font-size: 2rem;
                font-weight: 700;
                color: #fff;
            }}
            .stat-val.gold {{ color: var(--gold); }}
            .panel {{
                background: var(--surface-card);
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
            }}
            .panel-header {{
                padding: 20px 25px;
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .panel-title {{
                font-family: 'Cinzel', serif;
                font-size: 1.15rem;
                color: #fff;
                letter-spacing: 1px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: left;
            }}
            th {{
                padding: 14px 20px;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: var(--muted);
                background: rgba(255,255,255,0.02);
                border-bottom: 1px solid var(--border);
            }}
            td {{
                padding: 18px 20px;
                font-size: 0.88rem;
                border-bottom: 1px solid var(--border);
                vertical-align: middle;
            }}
            tr:hover td {{
                background: rgba(223,186,115,0.02);
            }}
            .booking-ref {{
                font-family: monospace;
                font-weight: 700;
                color: var(--gold);
                background: rgba(223,186,115,0.1);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.82rem;
            }}
            .email-tag {{
                font-size: 0.82rem;
                color: var(--blue);
            }}
            .badge-link {{
                display: inline-block;
                background: rgba(56, 189, 248, 0.12);
                color: var(--blue);
                border: 1px solid rgba(56, 189, 248, 0.3);
                padding: 6px 12px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 0.78rem;
                font-weight: 600;
                transition: background 0.2s;
            }}
            .badge-link:hover {{
                background: rgba(56, 189, 248, 0.25);
            }}
            .badge-studio {{
                display: inline-block;
                background: rgba(223, 186, 115, 0.12);
                color: var(--gold);
                border: 1px solid rgba(223, 186, 115, 0.3);
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.78rem;
                font-weight: 600;
            }}
            .status-badge {{
                display: inline-block;
                background: rgba(34, 197, 94, 0.12);
                color: var(--green);
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            footer {{
                text-align: center;
                padding: 25px;
                color: var(--muted);
                font-size: 0.8rem;
                border-top: 1px solid var(--border);
                margin-top: 40px;
            }}
        </style>
        <script>
            // Auto-refresh dashboard every 10 seconds to catch live bookings
            setTimeout(() => {{ location.reload(); }}, 10000);
        </script>
    </head>
    <body>
        <nav>
            <div>
                <div class="logo">{logo_icon} {settings.STORE_NAME}</div>
                <div class="tagline">{tagline}</div>
            </div>
            <div class="nav-actions">
                <a href="/lookbook" target="_blank" class="btn-lookbook">{btn_lookbook_text}</a>
            </div>
        </nav>

        <div class="main-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Appointments</div>
                    <div class="stat-val gold">{total_appts}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{card2_label}</div>
                    <div class="stat-val">{card2_val}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{card3_label}</div>
                    <div class="stat-val">{card3_val}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{card4_label}</div>
                    <div class="stat-val">{card4_val}</div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">{panel_title}</div>
                    <span style="font-size:0.78rem; color:var(--muted);">Auto-refreshes every 10s • Live Data</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Ref #</th>
                            <th>{th_client}</th>
                            <th>Email Address</th>
                            <th>Scheduled Date & Time</th>
                            <th>{th_product}</th>
                            <th>{th_mode}</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            {settings.STORE_NAME} Staff Concierge Management • {settings.STORE_ADDRESS}
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=admin_html, status_code=200)


