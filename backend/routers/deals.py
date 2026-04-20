from fastapi import APIRouter, Query
from services.rss import get_cached_deals, refresh_deals_cache

router = APIRouter(tags=["Deals"])


@router.get("/deals")
async def get_deals(
    category: str = Query(default="all", description="Filter by category"),
    search: str = Query(default=None, description="Search keyword"),
):
    return get_cached_deals(category=category, search=search)


@router.post("/deals/refresh")
async def force_refresh():
    await refresh_deals_cache()
    return {"status": "refreshed"}
