"""Startup script for Diyama Jewellers WhatsApp API backend."""

import sys
import uvicorn
from app.config import settings

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print("=" * 60)
    print("💎 Starting Diyama Jewellers WhatsApp API Server")
    print(f"📍 Webhook URL: http://localhost:{settings.PORT}/webhook")
    print(f"📊 Dashboard / Health: http://localhost:{settings.PORT}/")
    print(f"🛍️ Meta Commerce Catalog CSV: http://localhost:{settings.PORT}/catalog/meta-feed.csv")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
