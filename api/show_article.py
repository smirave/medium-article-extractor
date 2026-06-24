from fastapi import APIRouter, HTTPException
from pathlib import Path
import re

from utils.parser import parse_fm

router = APIRouter(
    prefix="/api",
    tags=["articles"]
)


@router.get("/articles/{slug}")
async def show_article(slug: str):

    path = Path("output") / slug / "article.md"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Article not found"
        )

    raw = path.read_text(
        encoding="utf-8"
    )

    meta = parse_fm(raw)

    body = re.sub(
        r"^---[\s\S]*?---\n",
        "",
        raw
    ).strip()

    return {
        "slug": slug,
        "meta": meta,
        "body": body,
        "images_dir": str(
            path.parent / "images"
        )
    }