"""Jewellery Catalog Data for Diyama Jewellers Demo."""

from typing import Dict, List, Optional
from pydantic import BaseModel

class Product(BaseModel):
    id: str
    retailer_id: str  # Matches WhatsApp Commerce Catalog retailer_id
    title: str
    category: str
    subcategory: str
    price_formatted: str
    price_amount: float
    currency: str
    gold_metal: str
    diamond_specs: str
    certification: str
    description: str
    image_url: str

# Curated High-Definition Jewellery Catalog for Diyama Jewellers
PRODUCTS: Dict[str, Product] = {
    # ------------------ RINGS ------------------
    "ring_solitaire": Product(
        id="ring_solitaire",
        retailer_id="DIY-RNG-0101",
        title="Aura Solitaire Diamond Ring (1.50ct)",
        category="Rings",
        subcategory="Solitaire Rings",
        price_formatted="₹2,45,000",
        price_amount=245000,
        currency="INR",
        gold_metal="18K White Gold (4.2g)",
        diamond_specs="1.50 Carat Round Brilliant, Color D, VVS1",
        certification="GIA Certified & Hallmarked",
        description="Handcrafted 6-prong crown solitaire ring engineered to maximize diamond fire and light refraction.",
        image_url="https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=800&q=80"
    ),
    "ring_halo": Product(
        id="ring_halo",
        retailer_id="DIY-RNG-0102",
        title="Celestial Rose Gold Halo Ring",
        category="Rings",
        subcategory="Halo & Cluster Rings",
        price_formatted="₹1,85,000",
        price_amount=185000,
        currency="INR",
        gold_metal="18K Rose Gold (3.8g)",
        diamond_specs="1.10 Carat Center + 0.35ct Micro-Pavé Halo, Color E, VVS2",
        certification="IGI Certified",
        description="A radiant center stone surrounded by a delicate halo of micro-pavé diamonds on a tapering rose gold band.",
        image_url="https://images.unsplash.com/photo-1603561591411-07134e71a2a9?auto=format&fit=crop&w=800&q=80"
    ),
    "ring_eternity": Product(
        id="ring_eternity",
        retailer_id="DIY-RNG-0103",
        title="Lumina Full Eternity Diamond Band",
        category="Rings",
        subcategory="Eternity Bands",
        price_formatted="₹1,65,000",
        price_amount=165000,
        currency="INR",
        gold_metal="Platinum 950 (5.8g)",
        diamond_specs="2.20 Carat Total Weight, Round Cut F-G Color, VS1",
        certification="In-house Master Hallmark & SGL",
        description="A complete unbroken circle of hand-matched brilliant diamonds symbolizing everlasting eternity.",
        image_url="https://images.unsplash.com/photo-1598560917505-59a3ad559071?auto=format&fit=crop&w=800&q=80"
    ),

    # ------------------ WEDDING RINGS ------------------
    "wed_couple_gold": Product(
        id="wed_couple_gold",
        retailer_id="DIY-WED-0201",
        title="Heritage Royal Couple Wedding Bands",
        category="Wedding Rings",
        subcategory="Couple Bands",
        price_formatted="₹1,40,000 (Set)",
        price_amount=140000,
        currency="INR",
        gold_metal="18K Yellow Gold (9.5g Combined)",
        diamond_specs="Hers: 0.15ct Secret Flush-Set Diamond",
        certification="BIS 916 Hallmarked",
        description="Luxurious matched comfort-fit wedding bands for Bride and Groom, with complimentary custom date engraving.",
        image_url="https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=800&q=80"
    ),
    "wed_platinum_duo": Product(
        id="wed_platinum_duo",
        retailer_id="DIY-WED-0202",
        title="Aethelgard Platinum Bridal Duo",
        category="Wedding Rings",
        subcategory="Platinum Bands",
        price_formatted="₹1,95,000 (Set)",
        price_amount=195000,
        currency="INR",
        gold_metal="Pure Platinum 950 (11.2g Combined)",
        diamond_specs="Hers: Channel-set 0.45ct Princess Cut Diamonds",
        certification="PGI Platinum Guild Certified",
        description="Modern sleek satin-finish groom band paired with an exquisite channel-set diamond bridal ring.",
        image_url="https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80"
    ),
    "wed_pave_band": Product(
        id="wed_pave_band",
        retailer_id="DIY-WED-0203",
        title="Seraphina French Pavé Wedding Ring",
        category="Wedding Rings",
        subcategory="Diamond Bands",
        price_formatted="₹98,000",
        price_amount=98000,
        currency="INR",
        gold_metal="18K White Gold (2.9g)",

        diamond_specs="0.65 Carat French Pavé Diamonds, Color E, VVS",
        certification="GIA Gemstone Report",
        description="Designed to contour seamlessly beside solitaire engagement rings with zero gap.",
        image_url="https://images.unsplash.com/photo-1588444837495-c6cfeb53f32d?auto=format&fit=crop&w=800&q=80"
    ),
}

def get_product(product_id: str) -> Optional[Product]:
    return PRODUCTS.get(product_id)

def get_product_by_retailer_id(retailer_id: str) -> Optional[Product]:
    for prod in PRODUCTS.values():
        if prod.retailer_id.lower() == retailer_id.lower():
            return prod
    return None

def get_products_by_category(category_name: str) -> List[Product]:
    return [p for p in PRODUCTS.values() if p.category.lower() == category_name.lower()]
