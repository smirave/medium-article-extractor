import threading

from extract import scrape

scraping_lock = threading.Lock()

scrape_status = {
    "running": False,
    "url": ""
}


def run_scrape(url: str):

    try:
        scrape(url)

    except Exception as e:
        print("Scrape failed:", e)

    finally:
        with scraping_lock:
            scrape_status["running"] = False
            scrape_status["url"] = ""