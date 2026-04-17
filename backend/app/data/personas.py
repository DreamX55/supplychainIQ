"""
Demo personas for SupplyChainIQ.

Each persona is a one-click preset that pre-fills the user profile
and supply chain description so judges can sweep through three
distinct industries in under 30 seconds. Pick one → analysis runs
immediately with a story-rich scenario.
"""

from typing import List, Dict, Any


PERSONAS: List[Dict[str, Any]] = [
    {
        "id": "apparel_brand",
        "name": "Atlas Apparel Co.",
        "industry": "Textiles & Apparel",
        "tagline": "Mid-market clothing brand sourcing from South Asia for Europe & US",
        "icon": "shirt",
        "accent": "amber",
        "description": (
            "We're a mid-sized apparel brand with primary cotton fabric sourced from "
            "Bangladesh and India, garment assembly in Bangladesh and Vietnam, and "
            "containerized shipping to European retailers via the Suez Canal and Red Sea. "
            "We also serve US East Coast distribution centers through the same lane. "
            "Lead times are tight and seasonal — we ship four collections a year and "
            "need to flag any disruption that would push delivery past our retailer "
            "windows."
        ),
    },
    {
        "id": "electronics_oem",
        "name": "Helix Electronics",
        "industry": "Electronics & Semiconductors",
        "tagline": "Consumer electronics OEM with Taiwan-Vietnam-Singapore-US chain",
        "icon": "cpu",
        "accent": "blue",
        "description": (
            "We manufacture consumer electronics. Our advanced semiconductors come "
            "from Taiwan (TSMC and partners), passive components from China, final "
            "assembly happens in Vietnam, and finished goods are transshipped through "
            "Singapore to the US West Coast. We have a 12-week production cycle and "
            "a high single-source dependency on Taiwan for our most expensive BoM "
            "line items. Geopolitical risk is our biggest unknown."
        ),
    },
    {
        "id": "agri_exporter",
        "name": "Verdant Foods",
        "industry": "Food & Beverage",
        "tagline": "Premium coffee & spice exporter from India to Europe & US",
        "icon": "leaf",
        "accent": "emerald",
        "description": (
            "We're a premium agricultural exporter shipping coffee beans from India "
            "and spices from Indonesia to specialty roasters and retailers in Europe "
            "and the United States. Our shipments move via maritime freight from "
            "Mumbai and Jakarta, transit through Singapore, and reach Rotterdam and "
            "the US East Coast. We're particularly sensitive to monsoon-season "
            "disruption, port congestion, and Red Sea routing decisions for our "
            "European customers."
        ),
    },
]


def get_personas() -> List[Dict[str, Any]]:
    """Return the list of demo personas."""
    return PERSONAS
