"""WhatsApp Cloud API Client for Diyama Jewellers."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger("whatsapp_client")
logging.basicConfig(level=logging.INFO)

class WhatsAppClient:
    @property
    def api_url(self) -> str:
        return settings.messages_endpoint

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

    async def _post_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends JSON payload to Meta Graph API with automatic retry on transient 500 errors."""
        if not settings.is_meta_configured:
            logger.warning(
                "[SIMULATION MODE] Meta credentials not configured in .env yet. "
                "Logging outbound payload instead of sending: %s", payload
            )
            return {"status": "simulated", "payload": payload}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(2):
                try:
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload
                    )
                    res_data = response.json()
                    # Meta 500 (131000) is a transient server-side glitch; retry once
                    if response.status_code == 500 and attempt == 0:
                        logger.warning("Meta 500 transient glitch. Auto-retrying in 1s... (fbtrace: %s)", res_data.get("fbtrace_id"))
                        await asyncio.sleep(1.0)
                        continue

                    if response.status_code >= 400:
                        logger.error("Meta API error (%s): %s | Outbound payload: %s", response.status_code, res_data, payload)
                    else:
                        logger.info("Meta API success (%s): %s", response.status_code, res_data)
                    return res_data
                except Exception as e:
                    if attempt == 0:
                        await asyncio.sleep(1.0)
                        continue
                    logger.error("Exception calling Meta Graph API: %s | Payload: %s", str(e), payload)
                    return {"error": str(e)}


    async def mark_as_read(self, message_id: str, show_typing: bool = True) -> Dict[str, Any]:
        """
        Marks an incoming WhatsApp message as read (displays double blue ticks)
        and activates the live animated 'typing...' indicator for the customer.
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        if show_typing:
            payload["typing_indicator"] = {"type": "text"}

        res = await self._post_payload(payload)

        # Graceful fallback: If typing_indicator is not supported, send standard read receipt
        if isinstance(res, dict) and "error" in res and show_typing:
            logger.info("Retrying mark_as_read without typing indicator...")
            payload.pop("typing_indicator", None)
            return await self._post_payload(payload)

        return res

    async def send_text(self, to: str, text: str, preview_url: bool = False) -> Dict[str, Any]:
        """Sends a standard text message."""

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url
            }
        }
        return await self._post_payload(payload)

    async def send_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],  # [{"id": "btn_1", "title": "Button 1"}] (max 3)
        header_text: Optional[str] = None,
        footer_text: Optional[str] = "Diyama Jewellers • Luxury Redefined"
    ) -> Dict[str, Any]:
        """Sends an interactive quick-reply button message (up to 3 buttons)."""
        button_components = []
        for btn in buttons[:3]:
            # Title max length 20 chars according to Meta specs
            title = btn.get("title", "")[:20]
            button_components.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id"),
                    "title": title
                }
            })

        interactive: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": button_components}
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        return await self._post_payload(payload)

    async def send_cta_url_button(
        self,
        to: str,
        body_text: str,
        button_text: str,
        url: str,
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an interactive Call-to-Action (CTA) URL button.
        When tapped in WhatsApp, it opens the web URL directly in the in-app browser!
        """
        interactive: Dict[str, Any] = {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": button_text[:20],
                    "url": url
                }
            }
        }
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text[:60]}
        if footer_text:
            interactive["footer"] = {"text": footer_text[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        return await self._post_payload(payload)

    async def send_list(
        self,
        to: str,
        body_text: str,
        button_label: str,  # Menu button label (e.g., "Choose Option")
        sections: List[Dict[str, Any]],  # [{"title": "...", "rows": [{"id": "..", "title": "..", "description": ".."}]}]
        header_text: Optional[str] = None,
        footer_text: Optional[str] = "Diyama Jewellers • Haute Joaillerie"
    ) -> Dict[str, Any]:
        """Sends an interactive list message (menu picker with up to 10 rows)."""
        # Automatically enforce Meta's strict length constraints (Section Title <= 24, Row Title <= 24, Row Desc <= 72)
        sanitized_sections = []
        for sec in sections:
            sanitized_rows = []
            for row in sec.get("rows", []):
                cleaned_row = {
                    "id": str(row.get("id")),
                    "title": str(row.get("title", ""))[:24]
                }
                if row.get("description"):
                    cleaned_row["description"] = str(row.get("description"))[:72]
                sanitized_rows.append(cleaned_row)

            sanitized_sections.append({
                "title": str(sec.get("title", ""))[:24],
                "rows": sanitized_rows
            })

        interactive: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_label[:20],
                "sections": sanitized_sections
            }
        }


        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        return await self._post_payload(payload)

    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends a high quality image with an optional caption."""
        image_payload: Dict[str, Any] = {"link": image_url}
        if caption:
            image_payload["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_payload
        }
        return await self._post_payload(payload)

    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: str,
        address: str
    ) -> Dict[str, Any]:
        """Sends a WhatsApp location pin."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address
            }
        }
        return await self._post_payload(payload)

    # ----------------------------------------------------
    # WHATSAPP COMMERCE NATIVE CATALOG METHODS
    # ----------------------------------------------------

    async def send_catalog_link(self, to: str, body_text: str = "Explore our certified jewellery collection inside WhatsApp:") -> Dict[str, Any]:
        """Sends a native WhatsApp catalog view button if Commerce Catalog is connected."""
        if not settings.META_CATALOG_ID:
            logger.info("META_CATALOG_ID not set. Skipping native catalog message.")
            return {"status": "catalog_not_configured"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "catalog_message",
                "body": {"text": body_text},
                "footer": {"text": "Diyama Jewellers Official Catalog"},
                "action": {
                    "name": "catalog_message"
                }
            }
        }
        return await self._post_payload(payload)

    async def send_native_product(
        self,
        to: str,
        product_retailer_id: str,
        body_text: str = "View product details & order directly:"
    ) -> Dict[str, Any]:
        """Sends a Single Product Message connected to Meta Commerce Catalog."""
        if not settings.META_CATALOG_ID:
            return {"status": "catalog_not_configured"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "product",
                "body": {"text": body_text},
                "footer": {"text": "Diyama Jewellers"},
                "action": {
                    "catalog_id": settings.META_CATALOG_ID,
                    "product_retailer_id": product_retailer_id
                }
            }
        }
        return await self._post_payload(payload)

    async def send_native_product_list(
        self,
        to: str,
        header_text: str,
        body_text: str,
        sections: List[Dict[str, Any]]  # [{"title": "...", "product_items": [{"product_retailer_id": "DIY-RNG-0101"}]}]
    ) -> Dict[str, Any]:
        """Sends a Multi-Product Message (MPM) connected to Meta Commerce Catalog."""
        if not settings.META_CATALOG_ID:
            return {"status": "catalog_not_configured"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "product_list",
                "header": {"type": "text", "text": header_text[:60]},
                "body": {"text": body_text},
                "footer": {"text": "Diyama Jewellers"},
                "action": {
                    "catalog_id": settings.META_CATALOG_ID,
                    "sections": sections
                }
            }
        }
        return await self._post_payload(payload)

whatsapp_client = WhatsAppClient()
