from pathlib import Path
import re

from fastapi import APIRouter

from utils.parser import parse_fm

router = APIRouter(
    prefix="/api",
    tags=["articles"]
)


@router.get("/articles")
async def get_articles():

    articles = []

    for f in sorted(
        Path("output").glob("*/article.md")
    ):

        raw = f.read_text(
            encoding="utf-8"
        )

        meta = parse_fm(raw)

        body = re.sub(
            r"^---[\s\S]*?---\n",
            "",
            raw
        ).strip()

        articles.append({
            "meta": meta,
            "body": body,
            "path": str(f),
            "images_dir": str(
                f.parent / "images"
            )
        })

    return articles