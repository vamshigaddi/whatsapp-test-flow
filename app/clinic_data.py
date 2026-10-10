"""Skin Care & Aesthetics Clinic Data Model and Catalog."""

from typing import Dict, List, Optional
from pydantic import BaseModel

class ClinicTreatment(BaseModel):
    id: str
    retailer_id: str
    title: str
    category: str
    price_formatted: str
    price_amount: float
    currency: str = "INR"
    duration: str
    doctor: str
    benefits: str
    description: str
    image_url: str

# Curated High-End Treatments for Dermatology & Aesthetics Clinic
CLINIC_TREATMENTS: Dict[str, ClinicTreatment] = {
    # ------------------ MEDI-FACIALS & GLOW ------------------
    "treat_hydrafacial": ClinicTreatment(
        id="treat_hydrafacial",
        retailer_id="AURA-HYD-0101",
        title="HydraFacial MD® Elite Glow",
        category="Medi-Facials & Glow",
        price_formatted="₹4,500",
        price_amount=4500,
        duration="45 Mins",
        doctor="Dr. Radhika Sharma, MD (Derm)",
        benefits="Deep Vortex Extraction, Hydration & Instant Radiance",
        description="US-FDA patented vortex technology to cleanse, extract impurities, and saturate skin with medical-grade antioxidants and hyaluronic peptides.",
        image_url="https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=800&q=80"
    ),
    "treat_carbon_peel": ClinicTreatment(
        id="treat_carbon_peel",
        retailer_id="AURA-CRB-0102",
        title="Hollywood Carbon Laser Peel",
        category="Medi-Facials & Glow",
        price_formatted="₹5,500",
        price_amount=5500,
        duration="40 Mins",
        doctor="Dr. Radhika Sharma, MD (Derm)",
        benefits="Pore Minimization, Oil Balancing & Porcelain Finish",
        description="Liquid carbon application paired with Q-switched Nd:YAG laser to gently vaporize dead cells, shrink enlarged pores, and illuminate complexion.",
        image_url="https://images.unsplash.com/photo-1560750588-73207b1ef5b8?auto=format&fit=crop&w=800&q=80"
    ),
    "treat_glass_skin": ClinicTreatment(
        id="treat_glass_skin",
        retailer_id="AURA-GLS-0103",
        title="Korean Glass Skin Infusion",
        category="Medi-Facials & Glow",
        price_formatted="₹6,999",
        price_amount=6999,
        duration="60 Mins",
        doctor="Dr. Sameer Khan, Senior Aesthetician",
        benefits="Intense Hydration, Translucent Sheen & Plumping",
        description="Nano-mesotherapy infusing pure hyaluronic skin-boosters, glutathione, and multivitamins combined with medical LED red light collagen therapy.",
        image_url="https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=800&q=80"
    ),

    # ------------------ LASER & CLINICAL PEELS ------------------
    "treat_laser_hair": ClinicTreatment(
        id="treat_laser_hair",
        retailer_id="AURA-LSR-0201",
        title="Triple-Wavelength Painless Laser",
        category="Laser & Skin Therapy",
        price_formatted="₹3,999 / Session",
        price_amount=3999,
        duration="30 Mins",
        doctor="Dr. Radhika Sharma, MD (Derm)",
        benefits="Permanent Hair Reduction with Ice-Cooling Comfort",
        description="Gold-standard combination of Alexandrite, Diode & Nd:YAG wavelengths suitable for all Indian skin types. 100% painless with contact sapphire cooling.",
        image_url="https://images.unsplash.com/photo-1519699047748-de8e457a634e?auto=format&fit=crop&w=800&q=80"
    ),
    "treat_acne_mnrf": ClinicTreatment(
        id="treat_acne_mnrf",
        retailer_id="AURA-MNR-0202",
        title="Acne Scar RF Microneedling (MNRF)",
        category="Laser & Skin Therapy",
        price_formatted="₹7,500 / Session",
        price_amount=7500,
        duration="50 Mins",
        doctor="Dr. Radhika Sharma, MD (Derm)",
        benefits="Collagen Remodeling, Scar Depth Reduction & Tightening",
        description="Radiofrequency micro-needling delivers targeted thermal energy into deep dermis to naturally fill pitted acne scars and restore smooth texture.",
        image_url="https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80"
    ),

    # ------------------ HAIR & SCALP RESTORATION ------------------
    "treat_gfc_hair": ClinicTreatment(
        id="treat_gfc_hair",
        retailer_id="AURA-GFC-0301",
        title="GFC Advanced Hair Regrowth",
        category="Hair & Scalp",
        price_formatted="₹6,500 / Session",
        price_amount=6500,
        duration="45 Mins",
        doctor="Dr. Sameer Khan, Senior Aesthetician",
        benefits="Arrests Hair Fall, Thickens Follicles & Boosts Density",
        description="Next-generation autologous Growth Factor Concentrate therapy. Pure platelets extracted and activated to trigger dormant hair roots with zero downtime.",
        image_url="https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?auto=format&fit=crop&w=800&q=80"
    )
}

def get_clinic_treatment(treatment_id: str) -> Optional[ClinicTreatment]:
    return CLINIC_TREATMENTS.get(treatment_id)

def get_treatments_by_category(category: str) -> List[ClinicTreatment]:
    return [t for t in CLINIC_TREATMENTS.values() if t.category.lower() == category.lower()]
