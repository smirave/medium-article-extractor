#!/usr/bin/env python3

import json
import re
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

R    = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
GRN  = "\033[38;5;114m"
CYN  = "\033[38;5;81m"
GRY  = "\033[38;5;245m"

W = lambda: shutil.get_terminal_size((80, 20)).columns

def divider(): print(f"{DIM}{GRY}{'─' * W()}{R}")
def ok(msg):   print(f"  {GRN}✓{R}  {msg}")
def info(k,v): print(f"  {GRY}{k:<12}{R}{BOLD}{v}{R}")


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        if self.path == "/api/articles":
            self.serve_articles()
        elif self.path.startswith("/output/"):
            self.serve_file()
        else:
            super().do_GET()

    def serve_articles(self):
        output = Path("output")
        articles = []

        for md_file in sorted(output.glob("*/article.md")):
            raw  = md_file.read_text(encoding="utf-8")
            meta = parse_frontmatter(raw)
            body = re.sub(r"^---[\s\S]*?---\n", "", raw).strip()
            articles.append({
                "meta": meta,
                "body": body,
                "path": str(md_file),
                "images_dir": str(md_file.parent / "images"),
            })

        data = json.dumps(articles, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self):
        path = Path(self.path.lstrip("/"))
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        ext  = path.suffix.lower()
        mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".gif":  "image/gif",
            ".webp":"image/webp", ".svg":  "image/svg+xml",
        }.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)


def parse_frontmatter(raw: str) -> dict:
    match = re.match(r"^---\n([\s\S]*?)\n---", raw)
    if not match:
        return {}
    obj = {}
    for line in match.group(1).split("\n"):
        if ": " not in line:
            continue
        k, *v = line.split(": ")
        val = ": ".join(v).strip().strip('"')
        if k == "tags":
            val = re.findall(r'"([^"]+)"', ": ".join(v))
        obj[k.strip()] = val
    return obj


if __name__ == "__main__":
    port = 8000
    print()
    divider()
    info("server",  f"http://localhost:{port}")
    info("articles", str(Path("output").resolve()))
    divider()
    ok("Open http://localhost:8000/reader.html in your browser")
    print()

    HTTPServer(("", port), Handler).serve_forever()