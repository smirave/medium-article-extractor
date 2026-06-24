#!/usr/bin/env python3

import json, re, shutil, subprocess, sys, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from extract import scrape

R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
GRN="\033[38;5;114m"; CYN="\033[38;5;81m"; GRY="\033[38;5;245m"; YLW="\033[38;5;221m"
W=lambda:shutil.get_terminal_size((80,20)).columns
def divider(): print(f"{DIM}{GRY}{'─'*W()}{R}")
def ok(m):    print(f"  {GRN}✓{R}  {m}")
def info(k,v):print(f"  {GRY}{k:<12}{R}{BOLD}{v}{R}")
def log(m):   print(f"  {CYN}→{R}  {m}")

# FIX: use the lock properly to prevent race conditions
scraping_lock = threading.Lock()
scrape_status = {"running": False, "url": ""}


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if   self.path == "/api/articles": self.api_articles()
        elif self.path == "/api/scrape/status": self.api_status()
        elif self.path.startswith("/output/"): self.serve_file()
        else: super().do_GET()

    def do_POST(self):
        if self.path == "/api/scrape":
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            self.api_scrape(body.get("url","").strip())

    def api_articles(self):
        arts = []
        for f in sorted(Path("output").glob("*/article.md")):
            raw  = f.read_text(encoding="utf-8")
            meta = parse_fm(raw)
            body = re.sub(r"^---[\s\S]*?---\n","",raw).strip()
            arts.append({"meta":meta,"body":body,"path":str(f),
                         "images_dir":str(f.parent/"images")})
        self._json(arts)

    def api_status(self):
        self._json(scrape_status)

    def api_scrape(self, url):
        if not url:
            self._json({"ok":False,"error":"No URL provided"}, 400); return
        if not url.startswith("http"):
            self._json({"ok":False,"error":"Invalid URL"}); return

        # FIX: use the lock to safely check + set the running flag atomically
        with scraping_lock:
            if scrape_status["running"]:
                self._json({"ok":False,"error":"Already scraping"}); return
            scrape_status["running"] = True
            scrape_status["url"]     = url

        self._json({"ok":True})
        threading.Thread(target=self._do_scrape, args=(url,), daemon=True).start()

    def _do_scrape(self, url):
        log(f"Scraping: {url}")
        try:
            scrape(url)
        except Exception as e:
            print(f"  ✖  Scrape failed: {e}")
        finally:
            # FIX: also use lock when clearing status
            with scraping_lock:
                scrape_status["running"] = False
                scrape_status["url"]     = ""

    def serve_file(self):
        path = Path(self.path.lstrip("/"))
        if not path.exists(): self.send_error(404); return
        data = path.read_bytes()
        mime = {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",
                ".gif":"image/gif",".webp":"image/webp",".svg":"image/svg+xml"
               }.get(path.suffix.lower(),"application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self._cors(); self.end_headers()
        self.wfile.write(data)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors(); self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")


def parse_fm(raw):
    m = re.match(r"^---\n([\s\S]*?)\n---", raw)
    if not m: return {}
    obj = {}
    for line in m.group(1).split("\n"):
        if ": " not in line: continue
        k,*v = line.split(": ")
        val  = ": ".join(v).strip().strip('"')
        if k=="tags": val = re.findall(r'"([^"]+)"', ": ".join(v))
        obj[k.strip()] = val
    return obj


if __name__=="__main__":
    port = 8002
    print()
    divider()
    info("server",   f"http://localhost:{port}")
    info("output",   str(Path("output").resolve()))
    divider()
    ok("Open http://localhost:8000/reader.html")
    print()
    HTTPServer(("",port), Handler).serve_forever()