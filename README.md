# 💎 Diyama Jewellers — WhatsApp Jewellery Enquiry & Appointment Bot

A production-grade, interactive WhatsApp conversational system for **Diyama Jewellers**, powered by **FastAPI** and the **Meta WhatsApp Cloud API**.

---

## 🌟 What This System Does

1. **Automated Welcoming Greeting**:
   - Responds to any customer contact with:
     > *"Thank you for contacting Diyama Jewellers. What are you searching for?"*
   - Presents an interactive WhatsApp menu with:
     - 💍 **Rings** (Solitaire, Halo, Eternity Bands)
     - 👰 **Wedding rings** (Couple Bands, Platinum Duo, Diamond Pavé)
     - 📅 **Appointment booking** (VIP Studio Visit or Virtual Google Meet)
     - 📍 **Location search** (Boutique map pin, directions & hours)

2. **In-WhatsApp Jewellery Browsing**:
   - Tapping **Rings** shows a selection of curated ring styles.
   - Selecting a ring immediately delivers:
     - 📸 **High-definition jewellery photo**
     - 🏷️ **Item code / SKU**
     - 💰 **Pricing** (e.g. `₹2,45,000 / $2,950`)
     - ⚜️ **Gold purity & weight** (e.g. `18K White Gold (4.2g)`)
     - ✨ **Diamond specifications** (e.g. `1.50ct Round Brilliant, D Color, VVS1`)
     - 📜 **Certification** (GIA / IGI Hallmarked)
     - 🔘 Instant action buttons: `[📅 Book Viewing]`, `[📍 Boutique Visit]`, `[🏠 Main Menu]`

3. **Complete Appointment Booking Engine**:
   - **Boutique Studio Visit** vs **Virtual Consultation (Google Meet)**.
   - Slot selection (Date & Time).
   - Generates unique reference code (e.g. `#DIY-9136`).
   - Generates and delivers **Google Meet room links** for virtual consultations.
   - Confirmation card with stylist assignment and reminders.

4. **Location & Studio Directions**:
   - Sends real WhatsApp **GPS Location Pin** + physical address, store timings, and Google Maps direct navigation link.

5. **WhatsApp Commerce Catalog Ready**:
   - Pre-built with Meta Commerce Manager integration.
   - Exports a ready-to-upload product CSV feed directly at `/catalog/meta-feed.csv`.

---

## 🚀 Quick Start Guide

### Step 1: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 2: Configure `.env`
Edit the `.env` file in the project root:
```env
WHATSAPP_TOKEN=your_meta_access_token_here
PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_BUSINESS_ACCOUNT_ID=your_waba_id_here
WEBHOOK_VERIFY_TOKEN=diyama_jewellers_secret_token_123
```

### Step 3: Start the FastAPI Server
```bash
python run.py
```
Or with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔑 Exactly What to Get From Meta for Developers

Go to [Meta for Developers](https://developers.facebook.com/) and open your App:

### 1. `WHATSAPP_TOKEN`
- In your App dashboard, go to **WhatsApp** -> **API Setup**.
- Look for **Temporary access token** (valid for 24h for rapid demo testing) OR generate a permanent **System User Token** in Meta Business Manager with permissions:
  - `whatsapp_business_messaging`
  - `whatsapp_business_management`
- Paste into `WHATSAPP_TOKEN`.

### 2. `PHONE_NUMBER_ID`
- In **WhatsApp** -> **API Setup**, look at **Step 1: Select phone numbers**.
- You will see:
  - *From*: Test phone number
  - *Phone number ID*: (A ~15-digit number, e.g. `104857291827461`)
- Copy and paste into `PHONE_NUMBER_ID`.

### 3. `WHATSAPP_BUSINESS_ACCOUNT_ID`
- In the same section right beneath Phone number ID:
  - *WhatsApp Business Account ID*: (e.g. `102938475610293`)
- Copy and paste into `WHATSAPP_BUSINESS_ACCOUNT_ID`.

### 4. `WEBHOOK_VERIFY_TOKEN`
- You can set any string you like, for example: `diyama_jewellers_secret_token_123`.
- Set the exact same string in your `.env` and in the Meta Webhook configuration dialog.

---

## 🌐 Exposing Your Local Server & Connecting Webhooks

Meta requires an **HTTPS** URL to deliver WhatsApp messages. You can use **ngrok** (or cloudflared / localtunnel):

1. Run ngrok in another terminal:
   ```bash
   npx ngrok http 8000
   ```
   Or:
   ```bash
   ngrok http 8000
   ```
2. You will get a forwarding URL like:
   `https://xyz-abc-123.ngrok-free.app`

3. In Meta App Dashboard:
   - Navigate to **WhatsApp** -> **Configuration**.
   - Under **Webhook**, click **Edit**.
   - **Callback URL**: `https://xyz-abc-123.ngrok-free.app/webhook`
   - **Verify token**: `diyama_jewellers_secret_token_123`
   - Click **Verify and save**.
   - Under **Webhook fields**, click **Manage** and subscribe to **`messages`**.

4. In **API Setup**, add your personal WhatsApp number under **To: Manage phone number list** (if using a test number).
5. Send "Hi" or "Hello" from your phone to the test number!

---

## 🛍️ How to Enable Meta Commerce Catalog for WhatsApp

WhatsApp Cloud API allows showing a native **"View Catalog"** button or sending **Single-Product Messages (SPM)** & **Multi-Product Messages (MPM)**.

Here is how to set it up:

### Method A: Use Meta Commerce Manager
1. Open [Meta Commerce Manager](https://business.facebook.com/commerce).
2. Click **Add Catalog** -> Select **E-commerce (Products)** -> Click **Next**.
3. Choose **Upload product info**, name it **Diyama Jewellers**, and click **Create**.
4. Go to **Catalog Settings** -> Copy the **Catalog ID** and paste it into your `.env`:
   ```env
   META_CATALOG_ID=your_catalog_id_here
   ```

### Method B: Upload the 2-3 Demo Products
Our backend automatically generates a standard Meta Product Feed CSV!
1. Start the server and download your pre-formatted CSV:
   - URL: `http://localhost:8000/catalog/meta-feed.csv`
2. In Commerce Manager -> **Data Sources** -> **Data feed**:
   - Choose **Upload file** and select the downloaded `diyama_jewellers_catalog.csv` (or enter your ngrok URL: `https://<ngrok-url>/catalog/meta-feed.csv` as a scheduled feed).
   - This instantly populates:
     - `DIY-RNG-0101` (Aura Solitaire Diamond Ring)
     - `DIY-RNG-0102` (Celestial Rose Gold Halo Ring)
     - `DIY-RNG-0103` (Lumina Full Eternity Band)
     - `DIY-WED-0201` (Heritage Royal Couple Bands)
     - `DIY-WED-0202` (Aethelgard Platinum Bridal Duo)
     - `DIY-WED-0203` (Seraphina French Pavé Wedding Ring)

### Method C: Link Catalog to your WhatsApp Business Account
1. In Meta Commerce Manager -> **Settings** -> **Business Assets**.
2. Click **WhatsApp Accounts** -> Connect your WhatsApp Business Account.
3. Toggle ON **"Enable Catalog on WhatsApp"**.

> 💡 **Note**: Even before Commerce Manager is approved, our system **already delivers rich interactive WhatsApp messages** with full jewellery images, certifications, gold karat weight, and prices!

---

## 🧪 Testing and Inspection Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /` | GET | Health dashboard & status check |
| `GET /webhook` | GET | Meta Webhook challenge verification |
| `POST /webhook` | POST | Meta incoming message & button event ingestion |
| `GET /catalog` | GET | View all jewellery items in JSON |
| `GET /catalog/meta-feed.csv` | GET | Download Meta Commerce Manager ready CSV |
| `GET /appointments` | GET | View all booked appointments & Google Meet links |
| `POST /test-simulate` | POST | Simulate user messages locally |
