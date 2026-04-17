"""
nlp_scorer.py — HuggingFace NER + Sentiment scoring for news disruption signals.
"""
import logging
from typing import Optional

import httpx

from backend.config import HF_API_TOKEN, FEATURES

logger = logging.getLogger("chainmind.nlp")

HF_BASE = "https://api-inference.huggingface.co/models"
NER_MODEL = "dslim/bert-base-NER"
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


async def score_text(text: str, client: Optional[httpx.AsyncClient] = None) -> dict:
    """Score a piece of text for disruption sentiment and named entities."""
    if not FEATURES["nlp_ner"]:
        return {
            "sentiment_label": "UNKNOWN",
            "sentiment_score": 0.5,
            "severity": 2,
            "entities": [],
            "source": "disabled",
        }

    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    truncated = text[:512]

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient()

    try:
        # Sentiment
        senti_resp = await client.post(
            f"{HF_BASE}/{SENTIMENT_MODEL}",
            json={"inputs": truncated},
            headers=headers,
            timeout=30.0,
        )
        sentiment_data = senti_resp.json() if senti_resp.status_code == 200 else None

        # NER
        ner_resp = await client.post(
            f"{HF_BASE}/{NER_MODEL}",
            json={"inputs": truncated},
            headers=headers,
            timeout=30.0,
        )
        ner_data = ner_resp.json() if ner_resp.status_code == 200 else None
    finally:
        if own_client:
            await client.aclose()

    # Process sentiment
    label = "NEUTRAL"
    senti_score = 0.5
    if sentiment_data and isinstance(sentiment_data, list) and sentiment_data:
        results = sentiment_data[0] if isinstance(sentiment_data[0], list) else sentiment_data
        if results:
            best = max(results, key=lambda x: x.get("score", 0))
            label = best.get("label", "NEUTRAL")
            senti_score = float(best.get("score", 0.5))
            if label == "POSITIVE":
                senti_score = 1 - senti_score  # Flip: positive = low disruption

    # Severity: 1–5
    severity = max(1, min(5, int(senti_score * 5) + 1))

    # Entities
    entities = []
    if ner_data and isinstance(ner_data, list):
        for item in ner_data:
            if isinstance(item, dict) and item.get("entity_group") in ("ORG", "LOC"):
                word = item.get("word", "").strip()
                if word and len(word) > 2 and not word.startswith("##"):
                    entities.append(word)
        entities = list(dict.fromkeys(entities))[:10]

    return {
        "sentiment_label": label,
        "sentiment_score": round(senti_score, 3),
        "severity": severity,
        "entities": entities,
        "source": "huggingface",
    }
