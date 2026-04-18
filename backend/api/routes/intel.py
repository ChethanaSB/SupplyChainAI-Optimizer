"""
intel.py (API route) — GET /api/intel/feed
Returns real-time "scraped" intelligence results around the ZF logistics network.
"""
import random
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Query
from backend.api.schemas import IntelResponse, IntelItem
from backend.data.ingestion.search_engine import search_engine

router = APIRouter()

INTEL_TEMPLATES = [
    {
        "title": "Red Sea Transit Delays Escalate",
        "summary": "Major shipping lines divert additional 15 vessels around the Cape of Good Hope, adding 12 days to Asia-Europe lead times.",
        "source": "Lloyd's List",
        "category": "LOGISTICS",
        "sentiment": "NEGATIVE",
        "url": "https://lloydslist.com/red-sea-disruption"
    },
    {
        "title": "Indian Rupee Stability Forecast",
        "summary": "RBI expected to maintain policy rates, supporting a stable INR/USD corridor for automotive component imports.",
        "source": "Bloomberg India",
        "category": "ECONOMY",
        "sentiment": "POSITIVE",
        "url": "https://bloomberg.com/inr-update"
    },
    {
        "title": "ZF Expands Pune Chakan Facility",
        "summary": "New phase of ZF's digitalization roadmap launched in India, focusing on AI-integrated logistics hubs.",
        "source": "Machinery Outlook",
        "category": "ZF_INTERNAL",
        "sentiment": "POSITIVE",
        "url": "https://zf.com/pune-expansion"
    },
    {
        "title": "Mundra Port Efficiency Hits Record High",
        "summary": "Automated berth allocation algorithms reduce vessel turnaround time to under 18 hours at Mundra.",
        "source": "Port Technology Intl",
        "category": "LOGISTICS",
        "sentiment": "POSITIVE",
        "url": "https://porttech.com/mundra-efficiency"
    },
    {
        "title": "Semi-conductor Lead Times Stabilize",
        "summary": "Global chip supply for automotive ECUs shows consistent 16-week lead time, down from 42 weeks in 2023.",
        "source": "TechCrunch Supply",
        "category": "ECONOMY",
        "sentiment": "POSITIVE",
        "url": "https://techcrunch.com/chips-supply"
    },
    {
        "title": "Cyclone Warning: Bay of Bengal",
        "summary": "High-pressure system developing off Chennai coast; port operations may be restricted for 48 hours starting Tuesday.",
        "source": "IMD Weather",
        "category": "WEATHER",
        "sentiment": "NEGATIVE",
        "url": "https://imd.gov.in/cyclone-alert"
    },
    {
        "title": "New Tariff Regulations: EU-India",
        "summary": "Simplified customs protocol for green-certified automotive parts expected to take effect next quarter.",
        "source": "The Economic Times",
        "category": "GEOPOLITICAL",
        "sentiment": "POSITIVE",
        "url": "https://economictimes.com/tariff-update"
    },
    {
        "title": "Oil Prices Surge on Middle East Tensions",
        "summary": "Brent crude hits $92/barrel, likely increasing fuel surcharges for air and road freight across South Asia.",
        "source": "Reuters Energy",
        "category": "ECONOMY",
        "sentiment": "NEGATIVE",
        "url": "https://reuters.com/oil-price"
    }
]

@router.get("/feed", response_model=IntelResponse)
async def get_intel_feed():
    """
    Fetch the latest 20 articles from Redis stream 'stream:news'.
    Falls back to synthetic templates if Redis is empty or unreachable.
    """
    from backend.data.ingestion.stream_bus import bus
    
    articles = []
    
    # 1. Try fetching from Redis
    if bus._redis:
        try:
            # Get last 20 messages from stream
            raw_data = await bus._redis.xrevrange("stream:news", count=20)
            for _, entry in raw_data:
                item_data = json.loads(entry["data"])
                articles.append(
                    IntelItem(
                        id=str(uuid.uuid4())[:8],
                        title=item_data.get("title", "No Title"),
                        summary=item_data.get("summary", ""), 
                        source=item_data.get("source", "Unknown"),
                        url=item_data.get("url", "#"),
                        timestamp=item_data.get("published_at") or item_data.get("_fetched_at"),
                        category="LOGISTICS", 
                        sentiment=item_data.get("sentiment_label", "NEUTRAL"),
                        relevance_score=item_data.get("sentiment_score", 0.5)
                    )
                )
        except Exception as exc:
            print(f"Error fetching from Redis stream: {exc}")

    # 2. Fallback to templates if no real news found
    if not articles:
        for _ in range(20):
            template = random.choice(INTEL_TEMPLATES)
            minutes_ago = random.randint(0, 1440)
            article_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
            articles.append(
                IntelItem(
                    id=str(uuid.uuid4())[:8],
                    title=template["title"],
                    summary=template["summary"],
                    source=template["source"],
                    url=template["url"],
                    timestamp=article_time.isoformat(),
                    category=template["category"],
                    sentiment=template["sentiment"],
                    relevance_score=round(random.uniform(0.75, 0.99), 2)
                )
            )
    
    # Sort by timestamp descending
    try:
        articles.sort(key=lambda x: x.timestamp, reverse=True)
    except:
        pass
    
    return IntelResponse(
        articles=articles[:20],
        computed_at=datetime.now(timezone.utc).isoformat()
    )

@router.get("/search")
async def global_search(q: str = Query(..., min_length=2)):
    """
    ZF Universal Search Engine: Returns mixed results (News + Topology).
    """
    # 1. Search News/Intel
    search_results = await search_engine.search(q, limit=5)
    
    # 2. Filter Topology (Plants/Suppliers)
    from backend.config import SUPPLIER_LOCATIONS, PLANT_LOCATIONS
    topology_results = []
    
    q_low = q.lower()
    for s in SUPPLIER_LOCATIONS:
        if q_low in s["id"].lower() or q_low in s["name"].lower():
            topology_results.append({"type": "SUPPLIER", "data": s})
            
    for p in PLANT_LOCATIONS:
        if q_low in p["id"].lower() or q_low in p["name"].lower():
            topology_results.append({"type": "PLANT", "data": p})

    return {
        "query": q,
        "news": [
            {
                "title": r["title"],
                "source": r["source"],
                "url": r["url"]
            } for r in search_results
        ],
        "topology": topology_results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
