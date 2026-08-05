import datetime
from typing import Any
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select

from app.api.deps import SessionDep
from app.models import Stock, StockNews
from app.services.news_service import fetch_stock_news_rss, analyze_news_sentiment

router = APIRouter()


@router.get("/{stock_id}/news")
def get_or_fetch_stock_news(stock_id: uuid.UUID, session: SessionDep) -> Any:
    """
    Get existing news from DB, or fetch live news if none exist.
    """
    stock = session.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # 1. Check if news already exists in DB
    existing_news = session.exec(
        select(StockNews)
        .where(StockNews.stock_id == stock_id)
        .order_by(StockNews.published_at.desc())
    ).all()

    if existing_news:
        return existing_news

    # 2. If no news found, fetch & analyze live
    raw_articles = fetch_stock_news_rss(stock.symbol, stock.name, max_results=3)
    saved_articles = []

    for item in raw_articles:
        sentiment_data = analyze_news_sentiment(item["title"], stock.name)

        news_obj = StockNews(
            stock_id=stock.id,
            title=item["title"],
            url=item["link"],
            source=item["source"],
            published_at=datetime.now(datetime.timezone.utc),
            sentiment=sentiment_data.get("sentiment", "NEUTRAL"),
            score=sentiment_data.get("score", 0.0),
            positive_points=sentiment_data.get("positive_points", []),
            negative_points=sentiment_data.get("negative_points", [])
        )
        session.add(news_obj)
        saved_articles.append(news_obj)

    session.commit()
    return saved_articles