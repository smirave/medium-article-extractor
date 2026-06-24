from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException
)
from fastapi.responses import FileResponse

from services.scraper import (
    scrape_status,
    scraping_lock,
    run_scrape
)

router = APIRouter(
    prefix="/api",
    tags=["scrape"]
)


@router.get("/scrape/status")
async def status():
    return scrape_status


@router.post("/scrape")
async def scrape_url(
    data: dict,
    background_tasks: BackgroundTasks
):

    url = data.get("url", "").strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="No URL provided"
        )

    if not url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL"
        )

    with scraping_lock:

        if scrape_status["running"]:
            raise HTTPException(
                status_code=409,
                detail="Already scraping"
            )

        scrape_status["running"] = True
        scrape_status["url"] = url

    background_tasks.add_task(
        run_scrape,
        url
    )

    return {
        "ok": True
    }


@router.get("/output/{file_path:path}")
async def files(file_path: str):

    path = Path("output") / file_path

    if not path.exists():
        raise HTTPException(404)

    return FileResponse(path)