"""Bot Router and Conversation Flow for Diyama Jewellers."""

import asyncio
import logging
from typing import Any, Dict, Optional
from app.config import settings
from app.catalog_data import PRODUCTS, get_product, get_products_by_category
from app.clinic_data import (
    CLINIC_TREATMENTS,
    get_clinic_treatment,
    get_treatments_by_category,
)
from app.appointments import (
    create_appointment,
    get_available_days,
    get_available_slots,
    BOOKINGS_DB,
)
from app.whatsapp_client import whatsapp_client

logger = logging.getLogger("bot_router")

# User session state tracker { phone_number: { "step": "...", "temp_booking": {...} } }
USER_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_session(phone: str) -> Dict[str, Any]:
    if phone not in USER_SESSIONS:
        USER_SESSIONS[phone] = {"step": "idle", "temp_booking": {}}
    return USER_SESSIONS[phone]

def reset_session(phone: str):
    USER_SESSIONS[phone] = {"step": "idle", "temp_booking": {}}


async def handle_incoming_message(msg: Dict[str, Any], sender_name: Optional[str] = None):
    """Processes any incoming WhatsApp message and routes to the appropriate flow."""
    from_phone = msg.get("from")
    msg_type = msg.get("type")
    msg_id = msg.get("id")

    logger.info("Handling incoming %s message from %s (Name: %s, ID: %s)", msg_type, from_phone, sender_name, msg_id)

    # Automatically mark message as read (blue ticks) and show live 'typing...' animation
    if msg_id:
        try:
            await whatsapp_client.mark_as_read(msg_id, show_typing=True)
            # Subtle realistic typing delay (0.7s) so customer experiences the animated typing bubble
            await asyncio.sleep(0.7)
        except Exception as e:
            logger.warning("Could not mark message as read / show typing: %s", e)


    if msg_type == "text":
        user_text = msg.get("text", {}).get("body", "").strip()
        await process_text_input(from_phone, user_text, sender_name)

    elif msg_type == "interactive":
        interactive_data = msg.get("interactive", {})
        sub_type = interactive_data.get("type")

        if sub_type == "button_reply":
            button_id = interactive_data.get("button_reply", {}).get("id")
            button_title = interactive_data.get("button_reply", {}).get("title")
            await process_action(from_phone, button_id, button_title, sender_name)

        elif sub_type == "list_reply":
            list_id = interactive_data.get("list_reply", {}).get("id")
            list_title = interactive_data.get("list_reply", {}).get("title")
            await process_action(from_phone, list_id, list_title, sender_name)

    else:
        # Fallback for voice notes, media, or other message types
        await send_main_menu(from_phone, sender_name)


async def send_main_menu(to: str, customer_name: Optional[str] = None):
    """
    Primary Welcome Greeting.
    Dynamically loads either Diyama Jewellers or Aesthetics Clinic based on BOT_MODE.
    """
    reset_session(to)
    name_str = f" {customer_name}" if customer_name else ""

    if settings.is_skincare_mode:
        body_text = (
            f"✨ *Welcome to {settings.STORE_NAME}*{name_str} ✨\n\n"
            "Thank you for contacting our clinic. How can our medical aesthetics & dermatology team assist you today?"
        )
        sections = [
            {
                "title": "Clinical Treatments",
                "rows": [
                    {
                        "id": "menu_facials",
                        "title": "🌟 Medi-Facials & Glow",
                        "description": "HydraFacial, Carbon Peel & Glass Skin"
                    },
                    {
                        "id": "menu_lasers",
                        "title": "⚡ Laser & Skin Therapy",
                        "description": "Laser Hair Reduction & Acne RF MNRF"
                    },
                    {
                        "id": "menu_hair",
                        "title": "🌿 Hair & Scalp Care",
                        "description": "GFC Therapy & Hair Fall Control"
                    },
                    {
                        "id": "menu_visual_catalogue",
                        "title": "🖼️ Treatment Showcase",
                        "description": "Photo guide with benefits & fees"
                    }
                ]
            },
            {
                "title": "Clinic & Doctors",
                "rows": [
                    {
                        "id": "menu_appointment",
                        "title": "📅 Book Doctor Consult",
                        "description": "Senior Dermatologist consultation"
                    },
                    {
                        "id": "menu_location",
                        "title": "📍 Clinic Location",
                        "description": "Jubilee Hills clinic address & timings"
                    }
                ]
            }
        ]

        await whatsapp_client.send_list(
            to=to,
            body_text=body_text,
            button_label="Explore Treatments",
            sections=sections,
            header_text=f"{settings.STORE_NAME}",
            footer_text="Board-Certified Dermatologists"
        )
        return

    # Clean, elegant core sections for Diyama Jewellers
    body_text = (
        f"✨ *Welcome to Diyama Jewellers*{name_str} ✨\n\n"
        "Thank you for contacting Diyama Jewellers. What are you searching for?"
    )

    sections = [
        {
            "title": "💎 Our Fine Collections",
            "rows": [
                {
                    "id": "menu_rings",
                    "title": "💍 Rings",
                    "description": "Solitaires, Halo & Eternity Diamond Rings"
                },
                {
                    "id": "menu_wedding_rings",
                    "title": "👰 Wedding rings",
                    "description": "Couple Bands, Platinum Duo & Pavé Sets"
                },
                {
                    "id": "menu_visual_catalogue",
                    "title": "🖼️ Visual Catalogue",
                    "description": "Full photo lookbook with specs & prices"
                }
            ]
        },
        {
            "title": "🛎️ Bespoke Services",
            "rows": [
                {
                    "id": "menu_appointment",
                    "title": "📅 Appointment booking",
                    "description": "VIP Studio Visit or Google Meet Virtual Call"
                },
                {
                    "id": "menu_location",
                    "title": "📍 Location search",
                    "description": "Find our luxury boutique address & directions"
                }
            ]
        }
    ]

    await whatsapp_client.send_list(
        to=to,
        body_text=body_text,
        button_label="Explore Menu",
        sections=sections,
        header_text="Diyama Jewellers • Flagship",
        footer_text="Certified Diamonds • Bespoke Craftsmanship"
    )


async def process_text_input(to: str, text: str, sender_name: Optional[str] = None):
    """Processes natural text input like 'Hi', 'Rings', 'HydraFacial', 'Appointment', etc."""
    text_lower = text.lower()
    session = get_session(to)

    # Check if user is in an active appointment flow
    if session.get("step") != "idle":
        await process_action(to, text, text, sender_name)
        return

    if settings.is_skincare_mode:
        if any(k in text_lower for k in ["catalog", "catalogue", "lookbook", "photo", "image", "gallery", "treatment", "showcase"]):
            await show_visual_catalogue(to)
        elif any(k in text_lower for k in ["facial", "glow", "hydra", "carbon", "glass"]):
            await show_clinic_category(to, "Medi-Facials & Glow")
        elif any(k in text_lower for k in ["laser", "hair", "acne", "peel", "rf", "mnrf", "skin"]):
            await show_clinic_category(to, "Laser & Skin Therapy")
        elif any(k in text_lower for k in ["hair", "gfc", "scalp", "fall"]):
            await show_clinic_category(to, "Hair & Scalp")
        elif any(k in text_lower for k in ["appointment", "booking", "consultation", "doctor", "dermatologist", "meet", "visit"]):
            await start_appointment_flow(to)
        elif any(k in text_lower for k in ["location", "address", "map", "clinic", "where", "timing"]):
            await show_location_info(to)
        else:
            await send_main_menu(to, sender_name)
        return

    # Direct keyword routing for Diyama Jewellers
    if any(k in text_lower for k in ["catalog", "catalogue", "lookbook", "photo", "image", "gallery"]):
        await show_visual_catalogue(to)
    elif any(k in text_lower for k in ["ring", "solitaire", "diamond ring"]):
        await show_rings_submenu(to)
    elif any(k in text_lower for k in ["wedding", "couple band", "bridal"]):
        await show_wedding_rings_submenu(to)
    elif any(k in text_lower for k in ["appointment", "booking", "consultation", "meet", "visit"]):
        await start_appointment_flow(to)
    elif any(k in text_lower for k in ["location", "address", "map", "store", "where", "timing"]):
        await show_location_info(to)
    else:
        # Default greeting / menu
        await send_main_menu(to, sender_name)


async def process_action(to: str, action_id: str, action_title: Optional[str] = None, sender_name: Optional[str] = None):
    """Handles button clicks, list selections, and booking states."""
    session = get_session(to)
    current_step = session.get("step", "idle")

    # 1. Main Navigation Actions
    if action_id == "menu_rings":
        await show_rings_submenu(to)
        return
    elif action_id == "menu_wedding_rings":
        await show_wedding_rings_submenu(to)
        return
    elif action_id == "menu_facials":
        await show_clinic_category(to, "Medi-Facials & Glow")
        return
    elif action_id == "menu_lasers":
        await show_clinic_category(to, "Laser & Skin Therapy")
        return
    elif action_id == "menu_hair":
        await show_clinic_category(to, "Hair & Scalp")
        return
    elif action_id == "menu_appointment":
        await start_appointment_flow(to)
        return
    elif action_id == "menu_location":
        await show_location_info(to)
        return
    elif action_id in ["menu_main", "btn_main_menu"]:
        await send_main_menu(to, sender_name)
        return
    elif action_id in ["menu_visual_catalogue", "menu_lookbook", "menu_commerce_catalog", "menu_catalog"]:
        await show_visual_catalogue(to)
        return

    # 2. Product / Treatment Details Selection
    if action_id.startswith("prod_"):
        prod_key = action_id.replace("prod_", "")
        await show_product_card(to, prod_key)
        return
    elif action_id.startswith("treat_"):
        await show_clinic_treatment_card(to, action_id)
        return

    # 3. Appointment Booking Step Machine
    if action_id == "book_for_product" or action_id.startswith("book_prod_") or action_id.startswith("book_treat_"):
        if action_id.startswith("book_treat_"):
            target_key = action_id.replace("book_treat_", "")
        elif action_id.startswith("book_prod_"):
            target_key = action_id.replace("book_prod_", "")
        else:
            target_key = None
        await start_appointment_flow(to, interested_product=target_key)
        return

    if current_step == "choose_type":
        # User selected Studio/Clinic Visit or Virtual Consultation
        if settings.is_skincare_mode:
            selected_type = "In-Clinic Consultation" if "studio" in action_id.lower() or "clinic" in action_id.lower() or "store" in action_id.lower() else "Virtual Skin Assessment (Google Meet)"
        else:
            selected_type = "In-Studio VIP Visit" if "studio" in action_id.lower() or "store" in action_id.lower() else "Virtual Consultation (Google Meet)"
        session["temp_booking"]["type"] = selected_type
        session["step"] = "choose_day"
        await ask_appointment_day(to, selected_type)
        return

    if current_step == "choose_day":
        session["temp_booking"]["day"] = action_title or action_id
        session["step"] = "choose_slot"
        await ask_appointment_slot(to)
        return

    if current_step == "choose_slot":
        session["temp_booking"]["slot"] = action_title or action_id
        selected_type = session["temp_booking"].get("type", "")
        # If Virtual Consultation, request customer email for Google Calendar invite
        if "Virtual" in selected_type or "Meet" in selected_type:
            session["step"] = "ask_email"
            await whatsapp_client.send_text(
                to=to,
                text=(
                    "📧 *Google Calendar & Meet Invitation*\n\n"
                    "Please reply with your **Email Address** so we can send the official Google Calendar invite and pre-consultation notes:"
                )
            )
            return
        else:
            # Clinic or Studio visit completes immediately
            await finalize_appointment(to, sender_name)
            return

    if current_step == "ask_email":
        user_email = (action_title or action_id or "").strip()
        session["temp_booking"]["email"] = user_email
        await finalize_appointment(to, sender_name)
        return

    # Fallback to main menu
    await send_main_menu(to, sender_name)



# ---------------------------------------------------------------------------
# CLINIC PROCEDURES & TREATMENTS FLOW (SKINCARE MODE)
# ---------------------------------------------------------------------------

async def show_clinic_category(to: str, category: str):
    """Shows clinical treatments for a chosen aesthetic dermatology category."""
    treatments = get_treatments_by_category(category)
    rows = []
    for t in treatments:
        rows.append({
            "id": t.id,
            "title": t.title[:24],
            "description": f"{t.price_formatted} • {t.duration} session"[:72]
        })

    sections = [{
        "title": category[:24],
        "rows": rows
    }]

    body = (
        f"✨ *{settings.STORE_NAME} • {category}*\n\n"
        "All procedures are administered using US-FDA approved technologies by board-certified dermatologists.\n\n"
        "Tap below to choose a treatment and review medical specs, doctor notes, and pricing:"
    )

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="View Procedures",
        sections=sections,
        header_text=f"{settings.STORE_NAME}",
        footer_text="Safe • Certified • US-FDA Approved"
    )


async def show_clinic_treatment_card(to: str, treat_id: str):
    """
    Displays rich clinical treatment card:
    - High-resolution clinical treatment photo
    - Pricing, duration, specialist doctor, benefits, overview
    - Interactive action buttons (Book Doctor / More Procedures / Main Menu)
    """
    treat = get_clinic_treatment(treat_id)
    if not treat:
        await whatsapp_client.send_text(to, "Treatment details are currently updating. Please select another procedure.")
        await show_clinic_category(to, "Medi-Facials & Glow")
        return

    caption = (
        f"✨ *{treat.title}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Code:* `{treat.retailer_id}`\n"
        f"💰 *Fee:* *{treat.price_formatted}*\n"
        f"⏱️ *Duration:* {treat.duration}\n"
        f"👩‍⚕️ *Specialist:* {treat.doctor}\n"
        f"🎯 *Key Benefits:* {treat.benefits}\n\n"
        f"📝 *Medical Overview:* {treat.description}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Would you like to reserve a doctor consultation or book this procedure?"
    )

    await whatsapp_client.send_image(
        to=to,
        image_url=treat.image_url,
        caption=caption
    )

    buttons = [
        {"id": f"book_treat_{treat.id}", "title": "📅 Book Doctor"},
        {"id": "menu_facials", "title": "🌟 More Treatments"},
        {"id": "menu_main", "title": "🏠 Main Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=f"How would you like to proceed with *{treat.title[:20]}*?",
        buttons=buttons,
        footer_text=f"{settings.STORE_NAME} Concierge"
    )


# ---------------------------------------------------------------------------
# PRODUCT BROWSING FLOWS (JEWELLERY MODE)
# ---------------------------------------------------------------------------

async def show_rings_submenu(to: str):
    """Shows Ring Types list to the customer."""
    rings = get_products_by_category("Rings")
    rows = []
    for r in rings:
        rows.append({
            "id": f"prod_{r.id}",
            "title": r.title[:24],
            "description": f"{r.price_formatted} • {r.diamond_specs[:40]}"
        })

    sections = [{
        "title": "Ring Designs",
        "rows": rows
    }]

    body = (
        "💍 *Diyama Exclusive Ring Collection*\n\n"
        "Each ring is masterfully cast in hallmarked precious metals and studded with hand-selected, certified diamonds.\n\n"
        "Tap below to choose a ring and inspect its full specifications, pricing, and imagery:"
    )

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="View Ring Types",
        sections=sections,
        header_text="Diyama Jewellers • Rings",
        footer_text="Tap to see certification & pricing"
    )


async def show_wedding_rings_submenu(to: str):
    """Shows Wedding Rings list to the customer."""
    wed_rings = get_products_by_category("Wedding Rings")
    rows = []
    for w in wed_rings:
        rows.append({
            "id": f"prod_{w.id}",
            "title": w.title[:24],
            "description": f"{w.price_formatted} • {w.gold_metal[:40]}"
        })

    sections = [{
        "title": "Wedding Band Styles",
        "rows": rows
    }]


    body = (
        "👰 *Diyama Bridal & Wedding Rings*\n\n"
        "Symbolize your eternal union with our signature wedding bands and bridal suites.\n\n"
        "Tap below to view styles, gold purity, pricing, and matching couple bands:"
    )

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="View Wedding Bands",
        sections=sections,
        header_text="Diyama Jewellers • Wedding",
        footer_text="Complimentary date engraving included"
    )


async def show_product_card(to: str, product_id: str):
    """
    Displays rich product details:
    - High-resolution jewellery image
    - Specifications (Metal, Diamond Grade, Certificate, SKU)
    - Pricing
    - Interactive action buttons (Book Viewing / Virtual Consult / Main Menu)
    """
    product = get_product(product_id)
    if not product:
        await whatsapp_client.send_text(to, "Jewellery item details are currently updating. Please select another piece.")
        await show_rings_submenu(to)
        return

    # Caption with complete jewellery specifications
    caption = (
        f"💎 *{product.title}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Item Code:* `{product.retailer_id}`\n"
        f"💰 *Price:* *{product.price_formatted}*\n"
        f"⚜️ *Metal:* {product.gold_metal}\n"
        f"✨ *Diamonds:* {product.diamond_specs}\n"
        f"📜 *Certification:* {product.certification}\n\n"
        f"📝 *Description:* {product.description}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Would you like to try this on in our boutique or inspect it on a live video consultation?"
    )

    # 1. Send the jewellery photo with specs
    await whatsapp_client.send_image(
        to=to,
        image_url=product.image_url,
        caption=caption
    )

    # 2. Dynamic, clean action buttons (no repetitive buttons)
    back_target = "menu_rings" if product.category == "Rings" else "menu_wedding_rings"
    back_label = "💍 More Rings" if product.category == "Rings" else "👰 More Bands"

    buttons = [
        {"id": f"book_prod_{product.id}", "title": "📅 Book Viewing"},
        {"id": back_target, "title": back_label},
        {"id": "menu_main", "title": "🏠 Main Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=f"How would you like to proceed with the *{product.title[:20]}*?",
        buttons=buttons,
        footer_text="Diyama Jewellers Concierge"
    )


async def show_visual_catalogue(to: str):
    """
    Delivers a visual catalogue directly in WhatsApp chat:
    - In Skincare Mode: Sends 3 aesthetic dermatology procedure photos with fees & benefits.
    - In Jewellery Mode: Sends 3 signature diamond rings with INR pricing & specs.
    """
    if settings.is_skincare_mode:
        intro = (
            f"✨ *{settings.STORE_NAME} • Treatment Showcase* ✨\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Here are our signature aesthetic dermatology procedures performed by specialist doctors:"
        )
        await whatsapp_client.send_text(to, intro)

        showcases = [
            CLINIC_TREATMENTS["treat_hydrafacial"],
            CLINIC_TREATMENTS["treat_carbon_peel"],
            CLINIC_TREATMENTS["treat_gfc_hair"]
        ]
        for t in showcases:
            caption = (
                f"🌟 *{t.title}*\n"
                f"💰 *Fee:* {t.price_formatted} ({t.duration})\n"
                f"👩‍⚕️ *Doctor:* {t.doctor}\n"
                f"🎯 *Benefits:* {t.benefits}\n"
                f"🏷️ *Code:* `{t.retailer_id}`"
            )
            await whatsapp_client.send_image(to, t.image_url, caption=caption)

        summary_text = (
            f"📖 *Full Clinical Treatment Menu:*\n"
            f"{settings.LOOKBOOK_URL}\n\n"
            f"*(Tap the link above to view all facial, laser, and hair therapies)*\n\n"
            f"Would you like to schedule an appointment with our dermatologist?"
        )

        buttons = [
            {"id": "book_treat_treat_hydrafacial", "title": "📅 Book Doctor"},
            {"id": "menu_lasers", "title": "⚡ Laser Therapies"},
            {"id": "menu_main", "title": "🏠 Main Menu"}
        ]

        await whatsapp_client.send_buttons(
            to=to,
            body_text=summary_text,
            buttons=buttons,
            footer_text=f"{settings.STORE_NAME} • Jubilee Hills"
        )
        return

    # Diyama Jewellers flow
    rings = get_products_by_category("Rings")

    # Send introductory text
    intro = (
        "💎 *Diyama Jewellers • Visual Catalogue* 💎\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Here are our signature certified diamond rings cast in 18K gold and platinum:"
    )
    await whatsapp_client.send_text(to, intro)

    # Deliver photos directly in chat
    for r in rings:
        caption = (
            f"💍 *{r.title}*\n"
            f"💰 *Price:* {r.price_formatted}\n"
            f"⚜️ *Metal:* {r.gold_metal}\n"
            f"✨ *Diamonds:* {r.diamond_specs}\n"
            f"📜 *Certification:* {r.certification}\n"
            f"🏷️ *Item Code:* `{r.retailer_id}`"
        )
        await whatsapp_client.send_image(to, r.image_url, caption=caption)

    # Provide Lookbook link & action buttons
    summary_text = (
        f"📖 *Full Digital Lookbook:*\n"
        f"{settings.LOOKBOOK_URL}\n\n"
        f"*(Tap the link above to view all pieces, bridal bands, and full specifications)*\n\n"
        f"Would you like to schedule a private viewing for any of these pieces?"
    )

    buttons = [
        {"id": "book_prod_ring_solitaire", "title": "📅 Book Viewing"},
        {"id": "menu_wedding_rings", "title": "👰 Wedding Bands"},
        {"id": "menu_main", "title": "🏠 Main Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=summary_text,
        buttons=buttons,
        footer_text="Diyama Jewellers • Banjara Hills"
    )




async def show_full_catalog(to: str):
    """
    Delivers a full-catalogue shopping experience directly inside WhatsApp
    using organized interactive department sections.
    """
    rings = get_products_by_category("Rings")
    weddings = get_products_by_category("Wedding Rings")

    sections = [
        {
            "title": "💍 Diamond Rings",
            "rows": [
                {
                    "id": f"prod_{p.id}",
                    "title": p.title[:24],
                    "description": f"{p.price_formatted} • {p.gold_metal[:25]}"
                }
                for p in rings
            ]
        },
        {
            "title": "👰 Wedding Bands",
            "rows": [
                {
                    "id": f"prod_{p.id}",
                    "title": p.title[:24],
                    "description": f"{p.price_formatted} • {p.gold_metal[:25]}"
                }
                for p in weddings
            ]
        }
    ]

    body = (
        "💎 *Diyama Jewellers • Complete Showcase*\n\n"
        "Explore our certified diamond rings and bespoke bridal collections.\n\n"
        "Tap below to choose any jewellery piece and inspect high-resolution imagery, diamond grading, karat weight, and pricing:"
    )

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="Browse Showcase",
        sections=sections,
        header_text="Diyama Jewellers • Showcase",
        footer_text="Bespoke Design • Certified Diamonds"
    )



# ---------------------------------------------------------------------------
# APPOINTMENT BOOKING FLOW
# ---------------------------------------------------------------------------

async def start_appointment_flow(to: str, interested_product: Optional[str] = None):
    """Step 1: Choose between In-Studio/Clinic visit or Virtual Consultation (Google Meet)."""
    session = get_session(to)
    session["step"] = "choose_type"
    session["temp_booking"] = {"product": interested_product}

    if settings.is_skincare_mode:
        session["temp_booking"]["type"] = "In-Clinic Doctor Consultation"
        session["step"] = "choose_day"
        await ask_appointment_day(to, "In-Clinic Doctor Consultation")
        return

    # Diyama Jewellers flow
    prod_note = ""
    if interested_product:
        p = get_product(interested_product)
        if p:
            prod_note = f"\n(Selected Piece: *{p.title}*)\n"

    body_text = (
        "💎 *Diyama Jewellers Appointment Booking*\n\n"
        f"We offer personalized one-on-one appointments with our master gemologists.{prod_note}\n"
        "Please choose your preferred consultation style:"
    )

    buttons = [
        {"id": "type_studio", "title": "🏬 Boutique Studio"},
        {"id": "type_virtual", "title": "💻 Virtual (Meet)"},
        {"id": "menu_main", "title": "🔙 Back to Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=body_text,
        buttons=buttons,
        header_text="VIP Consultation",
        footer_text="Complimentary champagne & private viewing"
    )


async def ask_appointment_day(to: str, selected_type: str):
    """Step 2: Choose preferred day."""
    days = get_available_days()
    rows = []
    for idx, d in enumerate(days):
        desc = "Doctor slot available" if settings.is_skincare_mode else "Exclusive slot available"
        rows.append({
            "id": f"day_{idx}",
            "title": d[:24],
            "description": desc
        })

    sections = [{
        "title": "Select Preferred Date",
        "rows": rows
    }]

    if settings.is_skincare_mode:
        session = get_session(to)
        prod_key = session.get("temp_booking", {}).get("product")
        treat_str = ""
        if prod_key:
            t = get_clinic_treatment(prod_key)
            if t:
                treat_str = f" for *{t.title}*"
        body = (
            f"✨ *Doctor Consultation Booking*{treat_str}\n\n"
            "Consult with our Senior MD Dermatologist at our Jubilee Hills clinic.\n\n"
            "Please select your preferred consultation day:"
        )
    else:
        body = (
            f"You selected: *{selected_type}*\n\n"
            "Please select your preferred consultation day:"
        )

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="Choose Date",
        sections=sections,
        header_text="Consultation Date"
    )


async def ask_appointment_slot(to: str):
    """Step 3: Choose time slot."""
    slots = get_available_slots()
    rows = []
    for idx, s in enumerate(slots):
        desc = "30-min doctor consultation" if settings.is_skincare_mode else "45-minute private styling session"
        rows.append({
            "id": f"slot_{idx}",
            "title": s[:24],
            "description": desc
        })

    sections = [{
        "title": "Select Time Slot",
        "rows": rows
    }]

    body = "Please choose a convenient time slot:"

    await whatsapp_client.send_list(
        to=to,
        body_text=body,
        button_label="Choose Slot",
        sections=sections,
        header_text="Consultation Time"
    )


async def finalize_appointment(to: str, customer_name: Optional[str] = None):
    """Step 4: Confirm appointment, generate Google Meet link if virtual, and send summary."""
    session = get_session(to)
    temp = session.get("temp_booking", {})

    default_type = "In-Clinic Consultation" if settings.is_skincare_mode else "In-Studio VIP Visit"
    appt_type = temp.get("type", default_type)
    day = temp.get("day", "Upcoming Day")
    slot = temp.get("slot", "11:30 AM")
    prod_key = temp.get("product")
    prod_name = None
    if prod_key:
        if settings.is_skincare_mode:
            t = get_clinic_treatment(prod_key)
            if t:
                prod_name = t.title
        else:
            p = get_product(prod_key)
            if p:
                prod_name = p.title

    user_email = temp.get("email")

    appt = create_appointment(
        phone_number=to,
        appointment_type=appt_type,
        day=day,
        time_slot=slot,
        customer_email=user_email,
        interested_product=prod_name,
        base_meet_url=settings.GOOGLE_MEET_BASE_URL
    )

    reset_session(to)

    if settings.is_skincare_mode:
        mode_section = (
            f"🏬 *Format:* In-Clinic Doctor Consultation\n"
            f"📍 *Clinic:* {settings.STORE_ADDRESS}\n"
        )

        concern_line = f"🩺 *Consultation For:* {appt.interested_product}\n" if appt.interested_product else ""

        summary_text = (
            "🎉 *Appointment Confirmed!* 🎉\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🔖 *Patient Ref ID:* `{appt.booking_id}`\n"
            f"👤 *Patient:* {customer_name or 'Valued Patient'}\n"
            f"📅 *Date:* {appt.day}\n"
            f"⏰ *Time Slot:* {appt.time_slot}\n"
            f"{concern_line}"
            f"{mode_section}"
            "━━━━━━━━━━━━━━━━━━\n"
            "Our patient care coordinator will call to confirm your medical history prior to your visit.\n"
            f"Thank you for choosing *{settings.STORE_NAME}*."
        )

        buttons = [
            {"id": "menu_location", "title": "📍 Clinic Location"},
            {"id": "menu_facials", "title": "🌟 View Treatments"},
            {"id": "menu_main", "title": "🏠 Main Menu"}
        ]

        await whatsapp_client.send_buttons(
            to=to,
            body_text=summary_text,
            buttons=buttons,
            header_text=f"{settings.STORE_NAME} • Confirmed",
            footer_text="Have questions? Reply anytime!"
        )
        return

    # Build confirmation message for Diyama Jewellers
    if appt.meet_url:
        email_str = f"📧 *Email Invite:* `{appt.customer_email}`\n" if appt.customer_email else ""
        mode_section = (
            f"💻 *Format:* Virtual Consultation\n"
            f"{email_str}"
            f"🔗 *Google Meet Link:* {appt.meet_url}\n"
            f"*(Join from phone or computer at the scheduled time)*\n"
        )
    else:
        mode_section = (
            f"🏬 *Format:* In-Store VIP Lounge\n"
            f"📍 *Location:* {settings.STORE_ADDRESS}\n"
            # f"🚗 *Valet Parking:* Complimentary at entrance\n"
        )

    product_line = f"💍 *Curated Piece:* {appt.interested_product}\n" if appt.interested_product else ""

    summary_text = (
        "🎉 *Appointment Confirmed!* 🎉\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *Booking Reference:* `{appt.booking_id}`\n"
        f"👤 *Guest:* {customer_name or 'Valued Patron'}\n"
        f"📅 *Date:* {appt.day}\n"
        f"⏰ *Time Slot:* {appt.time_slot}\n"
        f"{product_line}"
        f"{mode_section}"
        "━━━━━━━━━━━━━━━━━━\n"
        "Our dedicated jewellery specialist will also send a reminder 1 hour prior.\n"
        "Thank you for choosing *Diyama Jewellers*."
    )

    buttons = [
        {"id": "menu_location", "title": "📍 Store Directions"},
        {"id": "menu_rings", "title": "💍 Browse More Rings"},
        {"id": "menu_main", "title": "🏠 Main Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=summary_text,
        buttons=buttons,
        header_text="Diyama Jewellers • Booking Summary",
        footer_text="Have questions? Reply anytime!"
    )


# ---------------------------------------------------------------------------
# LOCATION & STORE / CLINIC INFO
# ---------------------------------------------------------------------------

async def show_location_info(to: str):
    """Sends official location pin and store/clinic opening hours."""
    # 1. Send WhatsApp native map pin
    await whatsapp_client.send_location(
        to=to,
        latitude=settings.STORE_LATITUDE,
        longitude=settings.STORE_LONGITUDE,
        name=settings.STORE_NAME,
        address=settings.STORE_ADDRESS
    )

    # 2. Send hours and contact
    if settings.is_skincare_mode:
        info_text = (
            f"📍 *{settings.STORE_NAME} Jubilee Hills*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Address:* {settings.STORE_ADDRESS}\n"
            f"🕒 *Timings:* {settings.STORE_HOURS}\n"
            f"📞 *Clinic Desk:* {settings.STORE_PHONE}\n"
            f"🗺️ *Directions:* {settings.GOOGLE_MAPS_LINK}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "State-of-the-art dermatology suites with dedicated doctor consultation rooms and valet parking."
        )
        buttons = [
            {"id": "menu_appointment", "title": "📅 Book Doctor"},
            {"id": "menu_facials", "title": "🌟 View Treatments"},
            {"id": "menu_main", "title": "🏠 Main Menu"}
        ]
        await whatsapp_client.send_buttons(
            to=to,
            body_text=info_text,
            buttons=buttons,
            footer_text=settings.STORE_NAME
        )
        return

    # Diyama Jewellers info
    info_text = (
        f"📍 *{settings.STORE_NAME} Luxury Studio*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Address:* {settings.STORE_ADDRESS}\n"
        f"🕒 *Timings:* {settings.STORE_HOURS}\n"
        f"📞 *Concierge:* {settings.STORE_PHONE}\n"
        f"🗺️ *Directions:* {settings.GOOGLE_MAPS_LINK}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "We look forward to welcoming you for an extraordinary jewellery experience."
    )

    buttons = [
        {"id": "menu_appointment", "title": "📅 Book VIP Visit"},
        {"id": "menu_rings", "title": "💍 View Rings"},
        {"id": "menu_main", "title": "🏠 Main Menu"}
    ]

    await whatsapp_client.send_buttons(
        to=to,
        body_text=info_text,
        buttons=buttons,
        footer_text="Diyama Jewellers"
    )
