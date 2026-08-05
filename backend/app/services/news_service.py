import feedparser
import json
from urllib.parse import quote
from openai import OpenAI
from fastapi import HTTPException

from app.core.config import settings


def fetch_stock_news_rss(symbol: str, company_name: str, max_results: int = 5):
    """Fetches real-time financial news for a specific stock via Google News RSS."""
    query = quote(f"{company_name} {symbol} stock news")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries[:max_results]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "source": getattr(entry, "source", {}).get("title", "Financial News"),
            "published": getattr(entry, "published", ""),
        })
    return articles


def analyze_news_sentiment(headline: str, company_name: str) -> dict:
    """Uses LLM to evaluate financial sentiment and extract key bullet points."""

    # Verify API key exists before instantiating client
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        # Fallback response if key is missing (prevents total app crash)
        return {
            "sentiment": "NEUTRAL",
            "score": 0.0,
            "positive_points": ["API key not configured"],
            "negative_points": []
        }

    # Initialize client dynamically per request or through settings
    client = OpenAI(api_key=api_key)

    prompt = f"""
    Analyze the following financial news headline for {company_name}:
    "{headline}"

    Provide output ONLY in JSON format matching this schema:
    {{
      "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
      "score": float between -1.0 (extremely bearish) and 1.0 (extremely bullish),
      "positive_points": ["point 1", "point 2"],
      "negative_points": ["point 1", "point 2"]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return {
            "sentiment": "NEUTRAL",
            "score": 0.0,
            "positive_points": [],
            "negative_points": []
        }