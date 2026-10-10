import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    @property
    def WHATSAPP_TOKEN(self) -> str:
        load_dotenv(BASE_DIR / ".env", override=True)
        return os.getenv("WHATSAPP_TOKEN", "").strip()

    @property
    def PHONE_NUMBER_ID(self) -> str:
        return os.getenv("PHONE_NUMBER_ID", "").strip()

    @property
    def WHATSAPP_BUSINESS_ACCOUNT_ID(self) -> str:
        return os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip()

    @property
    def WEBHOOK_VERIFY_TOKEN(self) -> str:
        return os.getenv("WEBHOOK_VERIFY_TOKEN", "diyama_jewellers_secret_token_123").strip()

    @property
    def META_GRAPH_API_VERSION(self) -> str:
        return os.getenv("META_GRAPH_API_VERSION", "v21.0").strip()

    @property
    def META_CATALOG_ID(self) -> str:
        return os.getenv("META_CATALOG_ID", "").strip()

    @property
    def BOT_MODE(self) -> str:
        """Active demo mode: 'jewellery' or 'skincare' (default: 'jewellery')."""
        load_dotenv(BASE_DIR / ".env", override=True)
        return os.getenv("BOT_MODE", "jewellery").strip().lower()

    @property
    def is_skincare_mode(self) -> bool:
        return self.BOT_MODE == "skincare"

    @property
    def STORE_NAME(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_NAME", "Aura Skin & Aesthetics Clinic")
        return os.getenv("STORE_NAME", "Diyama Jewellers")

    @property
    def STORE_ADDRESS(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_ADDRESS", "Aura Aesthetics Clinic, Road No. 36, Jubilee Hills, Hyderabad")
        return os.getenv("STORE_ADDRESS", "Diyama Jewellers Luxury Boutique, 42 Diamond Boulevard, Flagship Arcade")

    @property
    def STORE_LATITUDE(self) -> float:
        if self.is_skincare_mode:
            return float(os.getenv("CLINIC_LATITUDE", "17.4326"))
        return float(os.getenv("STORE_LATITUDE", "19.0760"))

    @property
    def STORE_LONGITUDE(self) -> float:
        if self.is_skincare_mode:
            return float(os.getenv("CLINIC_LONGITUDE", "78.4071"))
        return float(os.getenv("STORE_LONGITUDE", "72.8777"))

    @property
    def STORE_PHONE(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_PHONE", "+91 91234 56789")
        return os.getenv("STORE_PHONE", "+91 98765 43210")

    @property
    def STORE_HOURS(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_HOURS", "Mon - Sat: 10:00 AM - 8:00 PM (Sunday by Appt)")
        return os.getenv("STORE_HOURS", "Mon - Sun: 10:30 AM - 8:30 PM")

    @property
    def GOOGLE_MAPS_LINK(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_MAPS_LINK", "https://maps.google.com/?q=Jubilee+Hills+Hyderabad")
        return os.getenv("GOOGLE_MAPS_LINK", "https://maps.app.goo.gl/ZAbF7AQsXXjyF22q6?g_st=aw")

    @property
    def GOOGLE_MEET_BASE_URL(self) -> str:
        if self.is_skincare_mode:
            return os.getenv("CLINIC_MEET_BASE_URL", "https://meet.google.com/aura-skin-consult")
        return os.getenv("GOOGLE_MEET_BASE_URL", "https://meet.google.com/diy-diam-vip")

    @property
    def PUBLIC_URL(self) -> str:
        return os.getenv("PUBLIC_URL", "https://bucked-essential-bluff.ngrok-free.dev").rstrip("/")

    @property
    def LOOKBOOK_URL(self) -> str:
        return f"{self.PUBLIC_URL}/lookbook"

    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", "8000"))


    @property
    def is_meta_configured(self) -> bool:
        """Returns True if WhatsApp token and Phone Number ID are provided."""
        return bool(self.WHATSAPP_TOKEN and self.PHONE_NUMBER_ID and self.WHATSAPP_TOKEN != "PASTE_YOUR_META_ACCESS_TOKEN_HERE")

    @property
    def messages_endpoint(self) -> str:
        """Constructs the Meta Graph API messages endpoint."""
        return f"https://graph.facebook.com/{self.META_GRAPH_API_VERSION}/{self.PHONE_NUMBER_ID}/messages"

settings = Settings()

