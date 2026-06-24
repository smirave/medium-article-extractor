from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from api.articles import router as articles_router
from api.scrape import router as scrape_router

app = FastAPI(
    title="Scraper API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
   return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={}
)


app.include_router(articles_router)
app.include_router(scrape_router)