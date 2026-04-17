"""
Mock RAG Data for SupplyChainIQ Demo
Contains sample risk intelligence data for various supply chain scenarios
"""

GEOPOLITICAL_RISKS = [
    {
        "id": "geo_001",
        "region": "Taiwan",
        "category": "geopolitical",
        "risk_level": "High",
        "title": "Taiwan Strait Tensions",
        "description": "Ongoing geopolitical tensions in the Taiwan Strait region affecting semiconductor supply chains. Military exercises and diplomatic disputes create uncertainty for chip manufacturing and exports.",
        "affected_industries": ["electronics", "automotive", "computing"],
        "last_updated": "2024-03-15",
        "sources": ["Reuters", "Bloomberg", "CSIS Analysis"],
        "confidence": 0.89
    },
    {
        "id": "geo_002",
        "region": "Red Sea",
        "category": "geopolitical",
        "risk_level": "Critical",
        "title": "Red Sea Shipping Disruptions",
        "description": "Houthi attacks on commercial vessels have forced major shipping lines to reroute around Africa, adding 10-14 days to transit times and increasing freight costs by 200-300%.",
        "affected_industries": ["all", "retail", "manufacturing"],
        "last_updated": "2024-03-14",
        "sources": ["Lloyd's List", "Maersk Advisory", "UN Security Council"],
        "confidence": 0.95
    },
    {
        "id": "geo_003",
        "region": "Russia-Ukraine",
        "category": "geopolitical",
        "risk_level": "High",
        "title": "Eastern European Supply Route Disruptions",
        "description": "Ongoing conflict affecting overland transport routes through Eastern Europe. Sanctions impact raw material sourcing from Russia including palladium, nickel, and wheat.",
        "affected_industries": ["automotive", "agriculture", "energy"],
        "last_updated": "2024-03-10",
        "sources": ["European Commission", "World Bank"],
        "confidence": 0.92
    },
    {
        "id": "geo_004",
        "region": "South China Sea",
        "category": "geopolitical",
        "risk_level": "Medium",
        "title": "South China Sea Maritime Disputes",
        "description": "Territorial disputes affecting one of the world's busiest shipping lanes. 30% of global maritime trade transits through this region.",
        "affected_industries": ["shipping", "electronics", "energy"],
        "last_updated": "2024-03-12",
        "sources": ["CSIS", "Maritime Executive"],
        "confidence": 0.78
    }
]

CLIMATE_RISKS = [
    {
        "id": "clim_001",
        "region": "Panama Canal",
        "category": "climate",
        "risk_level": "High",
        "title": "Panama Canal Drought Restrictions",
        "description": "Severe drought conditions have reduced water levels in Gatun Lake, forcing the Panama Canal Authority to limit daily transits from 36 to 24 vessels. Wait times exceed 21 days.",
        "affected_industries": ["shipping", "lng", "containers"],
        "last_updated": "2024-03-14",
        "sources": ["Panama Canal Authority", "NOAA"],
        "confidence": 0.94
    },
    {
        "id": "clim_002",
        "region": "Southeast Asia",
        "category": "climate",
        "risk_level": "Medium",
        "title": "Monsoon Season Flooding Risk",
        "description": "Annual monsoon season (June-September) creates flooding risks for manufacturing facilities and logistics hubs in Thailand, Vietnam, and Bangladesh.",
        "affected_industries": ["apparel", "electronics", "automotive"],
        "last_updated": "2024-03-01",
        "sources": ["Asian Development Bank", "World Meteorological Organization"],
        "confidence": 0.85
    },
    {
        "id": "clim_003",
        "region": "Rhine River",
        "category": "climate",
        "risk_level": "Low",
        "title": "Rhine River Low Water Levels",
        "description": "Seasonal low water levels on the Rhine affect barge transport capacity for chemicals, coal, and industrial goods in Western Europe.",
        "affected_industries": ["chemicals", "energy", "manufacturing"],
        "last_updated": "2024-03-08",
        "sources": ["European Environment Agency"],
        "confidence": 0.72
    }
]

PORT_CONGESTION = [
    {
        "id": "port_001",
        "region": "Singapore",
        "category": "logistics",
        "risk_level": "Medium",
        "title": "Singapore Port Congestion",
        "description": "Increased vessel diversions from Red Sea have created congestion at Singapore terminals. Container dwell times increased 40%. Transshipment delays of 3-5 days.",
        "affected_industries": ["all"],
        "last_updated": "2024-03-15",
        "sources": ["Port of Singapore Authority", "Drewry"],
        "confidence": 0.88
    },
    {
        "id": "port_002",
        "region": "Los Angeles/Long Beach",
        "category": "logistics",
        "risk_level": "Low",
        "title": "US West Coast Port Operations Normal",
        "description": "Labor agreements in place through 2028. Port operations running smoothly with minimal delays. Average container dwell time at 2.5 days.",
        "affected_industries": ["retail", "automotive", "manufacturing"],
        "last_updated": "2024-03-14",
        "sources": ["Port of Los Angeles", "ILWU"],
        "confidence": 0.91
    },
    {
        "id": "port_003",
        "region": "Rotterdam",
        "category": "logistics",
        "risk_level": "Low",
        "title": "Rotterdam Operations Stable",
        "description": "Europe's largest port operating efficiently. Increased volumes from Red Sea rerouting being managed through additional berth capacity.",
        "affected_industries": ["all"],
        "last_updated": "2024-03-13",
        "sources": ["Port of Rotterdam"],
        "confidence": 0.87
    }
]

SUPPLIER_RISKS = [
    {
        "id": "sup_001",
        "region": "China",
        "category": "supplier",
        "risk_level": "Medium",
        "title": "Rare Earth Element Concentration",
        "description": "China controls 60% of rare earth mining and 90% of processing capacity. Export restrictions possible during trade tensions. Affects magnets, batteries, and electronics.",
        "affected_industries": ["electronics", "automotive", "renewable energy"],
        "last_updated": "2024-03-10",
        "sources": ["USGS", "IEA"],
        "confidence": 0.86
    },
    {
        "id": "sup_002",
        "region": "Vietnam",
        "category": "supplier",
        "risk_level": "Low",
        "title": "Vietnam Manufacturing Hub Growth",
        "description": "Vietnam emerging as alternative manufacturing hub. Strong growth in electronics assembly. Infrastructure improvements ongoing. Power grid stability improving.",
        "affected_industries": ["electronics", "apparel", "furniture"],
        "last_updated": "2024-03-12",
        "sources": ["Vietnam Ministry of Industry", "World Bank"],
        "confidence": 0.82
    },
    {
        "id": "sup_003",
        "region": "India",
        "category": "supplier",
        "risk_level": "Low",
        "title": "India Pharmaceutical Supply Stable",
        "description": "India supplies 40% of US generic drugs. Production capacity expanding. API sourcing from China remains a dependency to monitor.",
        "affected_industries": ["pharmaceutical", "healthcare"],
        "last_updated": "2024-03-11",
        "sources": ["FDA", "Indian Pharmaceutical Alliance"],
        "confidence": 0.84
    }
]

# Intra-country / regional risks. Surfaced when "Local Focus" mode is on.
# Each entry carries an extra `country` field so the RAG layer can boost
# matches against the user's focus_country.
INTRA_COUNTRY_RISKS = [
    {
        "id": "loc_in_001",
        "country": "India",
        "region": "Uttarakhand",
        "category": "logistics",
        "risk_level": "High",
        "title": "Dehradun-Mussoorie Highway Monsoon Closures",
        "description": "Annual monsoon (Jun-Sep) triggers landslides and washouts on NH-707, intermittently severing road freight to the Dehradun cluster. Detours via Haridwar add 6-9 hours to inbound truck transit.",
        "affected_industries": ["all", "fmcg", "pharmaceutical", "apparel"],
        "last_updated": "2024-07-22",
        "sources": ["NHAI Advisory", "Uttarakhand State DM Authority"],
        "confidence": 0.88,
        "transport_mode": "road"
    },
    {
        "id": "loc_in_002",
        "country": "India",
        "region": "Tamil Nadu",
        "category": "logistics",
        "risk_level": "Medium",
        "title": "Chennai Port Domestic Cargo Transit Delays",
        "description": "Coastal shipping and inland container movement out of Chennai Port facing 3-5 day dwell times due to truck driver shortages and gate congestion. Affects domestic auto and electronics OEMs in Hosur and Sriperumbudur.",
        "affected_industries": ["automotive", "electronics", "manufacturing"],
        "last_updated": "2024-08-04",
        "sources": ["Chennai Port Authority", "FIEO"],
        "confidence": 0.83,
        "transport_mode": "road"
    },
    {
        "id": "loc_in_003",
        "country": "India",
        "region": "Maharashtra",
        "category": "logistics",
        "risk_level": "High",
        "title": "Mumbai-Bangalore Trucking Strike Risk",
        "description": "Recurring transporter strikes on the Mumbai-Pune-Bangalore corridor over diesel pricing and toll hikes. Last strike (Mar 2024) halted ~40% of FMCG and apparel inbound freight for 4 days.",
        "affected_industries": ["fmcg", "apparel", "retail", "pharmaceutical"],
        "last_updated": "2024-07-30",
        "sources": ["All India Motor Transport Congress", "Economic Times"],
        "confidence": 0.85,
        "transport_mode": "road"
    },
    {
        "id": "loc_in_004",
        "country": "India",
        "region": "Assam",
        "category": "climate",
        "risk_level": "High",
        "title": "Northeast India Highway Landslide Season",
        "description": "NH-6 and NH-37 connecting Assam to the rest of the Northeast see 12-20 closure events per monsoon. Tea, bamboo, and small-scale electronics exports out of Guwahati face 7-14 day overland delays.",
        "affected_industries": ["agricultural", "tea", "electronics"],
        "last_updated": "2024-08-01",
        "sources": ["BRO Advisory", "Assam State Disaster Management"],
        "confidence": 0.86,
        "transport_mode": "road"
    },
    {
        "id": "loc_in_005",
        "country": "India",
        "region": "Punjab",
        "category": "logistics",
        "risk_level": "Medium",
        "title": "Punjab-Haryana Farmer Protest Road Blockades",
        "description": "Periodic farmer agitations block NH-44 and the Delhi-Amritsar corridor for 1-3 days at a time. Inland movement of textiles, auto components, and agri-inputs is disrupted with no maritime alternative.",
        "affected_industries": ["apparel", "automotive", "agricultural"],
        "last_updated": "2024-06-18",
        "sources": ["Ministry of Road Transport", "Reuters India"],
        "confidence": 0.80,
        "transport_mode": "road"
    },
    {
        "id": "loc_in_006",
        "country": "India",
        "region": "Karnataka",
        "category": "supplier",
        "risk_level": "Medium",
        "title": "Bangalore Power Grid Load Shedding",
        "description": "Peak summer (Apr-Jun) load shedding in Karnataka industrial belts causes 2-4 hours of daily disruption for unbacked manufacturing units. Electronics and auto-component SMEs report 8-12% throughput loss.",
        "affected_industries": ["electronics", "automotive", "manufacturing"],
        "last_updated": "2024-05-22",
        "sources": ["BESCOM", "Karnataka Industries Dept"],
        "confidence": 0.82,
        "transport_mode": None
    },
    {
        "id": "loc_in_007",
        "country": "India",
        "region": "Gujarat",
        "category": "logistics",
        "risk_level": "Low",
        "title": "Mundra Inland Rail Corridor Stable",
        "description": "Dedicated Freight Corridor (DFC) Western arm operating at 92% reliability. Mundra-to-NCR rail freight remains the most reliable domestic logistics lane in India.",
        "affected_industries": ["all", "retail", "manufacturing"],
        "last_updated": "2024-08-10",
        "sources": ["DFCCIL", "APM Terminals Mundra"],
        "confidence": 0.90,
        "transport_mode": "rail"
    }
]


ALTERNATIVE_SUPPLIERS = {
    "semiconductors": [
        {"country": "South Korea", "companies": ["Samsung", "SK Hynix"], "lead_time": "6-12 months"},
        {"country": "Japan", "companies": ["Renesas", "Kioxia"], "lead_time": "4-8 months"},
        {"country": "USA", "companies": ["Intel", "GlobalFoundries"], "lead_time": "12-18 months"},
        {"country": "Germany", "companies": ["Infineon"], "lead_time": "8-12 months"}
    ],
    "apparel": [
        {"country": "Bangladesh", "specialization": "Garments", "lead_time": "4-6 weeks"},
        {"country": "Vietnam", "specialization": "Footwear, Technical Apparel", "lead_time": "3-5 weeks"},
        {"country": "Indonesia", "specialization": "Textiles", "lead_time": "4-6 weeks"},
        {"country": "India", "specialization": "Cotton, Silk", "lead_time": "5-7 weeks"},
        {"country": "Mexico", "specialization": "Near-shoring", "lead_time": "2-3 weeks"}
    ],
    "electronics_assembly": [
        {"country": "Vietnam", "specialization": "Consumer Electronics", "lead_time": "4-6 weeks"},
        {"country": "Malaysia", "specialization": "Semiconductors, Testing", "lead_time": "4-8 weeks"},
        {"country": "Thailand", "specialization": "Hard Drives, Automotive", "lead_time": "4-6 weeks"},
        {"country": "Mexico", "specialization": "Near-shoring for US", "lead_time": "2-4 weeks"},
        {"country": "Poland", "specialization": "Near-shoring for EU", "lead_time": "2-4 weeks"}
    ],
    "agricultural": [
        {"country": "Brazil", "products": ["Soybeans", "Coffee", "Sugar"], "lead_time": "6-10 weeks"},
        {"country": "Argentina", "products": ["Corn", "Beef", "Soybeans"], "lead_time": "6-10 weeks"},
        {"country": "Australia", "products": ["Wheat", "Wool", "Beef"], "lead_time": "8-12 weeks"},
        {"country": "Canada", "products": ["Wheat", "Canola", "Lumber"], "lead_time": "2-4 weeks"}
    ]
}

SHIPPING_ROUTES = {
    "asia_to_us_west": {
        "primary": "Trans-Pacific Direct",
        "transit_time": "14-18 days",
        "alternatives": [
            {"route": "Via Mexico (Manzanillo)", "transit_time": "18-22 days", "benefit": "Avoid port congestion"},
            {"route": "Via Canada (Vancouver/Prince Rupert)", "transit_time": "12-15 days", "benefit": "Faster clearance"}
        ]
    },
    "asia_to_europe": {
        "primary": "Suez Canal Route",
        "transit_time": "28-32 days",
        "alternatives": [
            {"route": "Cape of Good Hope", "transit_time": "40-45 days", "status": "Currently in use due to Red Sea crisis"},
            {"route": "Trans-Siberian Rail", "transit_time": "18-22 days", "status": "Limited due to sanctions"}
        ]
    },
    "asia_to_us_east": {
        "primary": "Suez Canal + Atlantic",
        "transit_time": "35-40 days",
        "alternatives": [
            {"route": "Panama Canal", "transit_time": "25-30 days", "status": "Restricted due to drought"},
            {"route": "Cape + Atlantic", "transit_time": "45-50 days", "status": "Available"},
            {"route": "West Coast + Rail", "transit_time": "22-28 days", "benefit": "Intermodal option"}
        ]
    }
}


def get_all_risks():
    """Return all risk data combined"""
    return GEOPOLITICAL_RISKS + CLIMATE_RISKS + PORT_CONGESTION + SUPPLIER_RISKS + INTRA_COUNTRY_RISKS


def search_risks(query: str, regions: list = None, categories: list = None):
    """
    Search risks based on query terms, regions, and categories
    Simulates vector similarity search for demo purposes
    """
    all_risks = get_all_risks()
    results = []
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    for risk in all_risks:
        score = 0
        
        # Check region match
        if regions:
            if risk["region"].lower() in [r.lower() for r in regions]:
                score += 0.4
        
        # Check category match
        if categories:
            if risk["category"].lower() in [c.lower() for c in categories]:
                score += 0.2
        
        # Text matching (simulating semantic search)
        text_to_search = f"{risk['title']} {risk['description']} {risk['region']}".lower()
        
        for term in query_terms:
            if term in text_to_search:
                score += 0.15
            if term in risk["region"].lower():
                score += 0.2
            if any(term in ind.lower() for ind in risk["affected_industries"]):
                score += 0.1
        
        if score > 0:
            results.append({**risk, "relevance_score": min(score, 1.0)})
    
    # Sort by relevance score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:10]


def get_alternatives(industry: str):
    """Get alternative suppliers for an industry"""
    industry_lower = industry.lower()
    
    if "semiconductor" in industry_lower or "chip" in industry_lower or "electronic" in industry_lower:
        return ALTERNATIVE_SUPPLIERS.get("semiconductors", [])
    elif "apparel" in industry_lower or "cloth" in industry_lower or "textile" in industry_lower:
        return ALTERNATIVE_SUPPLIERS.get("apparel", [])
    elif "assembly" in industry_lower or "manufacturing" in industry_lower:
        return ALTERNATIVE_SUPPLIERS.get("electronics_assembly", [])
    elif "agricult" in industry_lower or "food" in industry_lower or "farm" in industry_lower:
        return ALTERNATIVE_SUPPLIERS.get("agricultural", [])
    
    return []


def get_shipping_alternatives(origin: str, destination: str):
    """Get alternative shipping routes"""
    origin_lower = origin.lower()
    dest_lower = destination.lower()
    
    if "asia" in origin_lower or "china" in origin_lower or "taiwan" in origin_lower or "vietnam" in origin_lower:
        if "us" in dest_lower or "america" in dest_lower or "united states" in dest_lower:
            if "west" in dest_lower or "california" in dest_lower:
                return SHIPPING_ROUTES.get("asia_to_us_west", {})
            elif "east" in dest_lower or "new york" in dest_lower:
                return SHIPPING_ROUTES.get("asia_to_us_east", {})
            else:
                return SHIPPING_ROUTES.get("asia_to_us_west", {})
        elif "europe" in dest_lower or "eu" in dest_lower:
            return SHIPPING_ROUTES.get("asia_to_europe", {})
    
    return {}
