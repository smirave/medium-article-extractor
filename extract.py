#!/usr/bin/env python3

import re
import sys
import time
import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup


R = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
RED  = "\033[38;5;203m"
GRN  = "\033[38;5;114m"
YLW  = "\033[38;5;221m"
CYN  = "\033[38;5;81m"
MGT  = "\033[38;5;177m"
GRY  = "\033[38;5;245m"

W = lambda: shutil.get_terminal_size((80, 20)).columns

def divider():
    print(f"{DIM}{GRY}{'─' * W()}{R}")

def tag(color, label):
    return f"{BOLD}{color} {label} {R}"

def log_step(n, total, icon, msg):
    counter = f"{GRY}[{n}/{total}]{R}"
    print(f"  {counter}  {icon}  {msg}")

def log_ok(msg):
    print(f"  {GRN}✓{R}  {msg}")

def log_warn(msg):
    print(f"  {YLW}⚠{R}  {GRY}{msg}{R}")

def log_err(msg):
    print(f"\n  {RED}✖  {msg}{R}\n")
    sys.exit(1)

def label(key, val):
    return f"  {GRY}{key:<10}{R}{BOLD}{val}{R}"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


def sanitize(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return re.sub(r"\s+", "_", name.strip())[:80]


def fetch(url: str) -> dict:
    print(f"\n  {CYN}Fetching{R}  {GRY}{url}{R}\n")

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 2:
                log_err(str(e))
            log_warn(f"Attempt {attempt + 1} failed — retrying…")
            time.sleep(2)

    soup  = BeautifulSoup(resp.text, "html.parser")
    title = ""

    for sel in ["h1", 'meta[property="og:title"]', "title"]:
        t = soup.select_one(sel)
        if t:
            title = t.get("content", "") or t.get_text(strip=True)
            if title:
                break

    author_tag = (
        soup.select_one('meta[name="author"]')
        or soup.select_one('[data-testid="authorName"]')
        or soup.select_one(".pw-author-name")
    )
    author = ""
    if author_tag:
        author = author_tag.get("content", "") or author_tag.get_text(strip=True)

    date_tag = soup.select_one("time") or soup.select_one('meta[property="article:published_time"]')
    date = ""
    if date_tag:
        date = (date_tag.get("datetime") or date_tag.get("content") or date_tag.get_text(strip=True))[:10]

    tags = list(dict.fromkeys(
        t.get_text(strip=True) for t in soup.select('a[href*="/tag/"]')
    ))[:8]

    body = (
        soup.select_one("article")
        or soup.select_one('[data-testid="post-content"]')
        or soup.select_one(".postArticle-content")
        or soup.select_one("main")
    )

    print(label("title",  title  or "—"))
    print(label("author", author or "—"))
    print(label("date",   date   or "—"))
    print(label("tags",   ", ".join(tags) if tags else "—"))

    return {"title": title, "author": author, "date": date, "tags": tags, "url": url, "body": body}


def download_img(url: str, save_dir: Path, idx: int, total: int) -> str | None:
    try:
        ext = Path(urlparse(url).path).suffix.lower()
        if ext not in IMAGE_EXTS:
            ext = ".jpg"

        fname = f"image_{idx:03d}{ext}"
        resp  = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        (save_dir / fname).write_bytes(resp.content)

        pct  = int(40 * idx / total)
        bar  = f"{GRN}{'█' * pct}{GRY}{'░' * (40 - pct)}{R}"
        size = f"{GRY}{len(resp.content) // 1024} KB{R}"
        print(f"\r  [{bar}]  {CYN}{idx}/{total}{R}  {GRY}{fname}{R}  {size}     ", end="", flush=True)

        return f"images/{fname}"
    except Exception as e:
        log_warn(f"Image {idx} skipped — {e}")
        return None


def to_markdown(data: dict, out_dir: Path) -> tuple[str, int]:
    imgs_dir = out_dir / "images"
    imgs_dir.mkdir(parents=True, exist_ok=True)

    total_imgs  = len(data["body"].find_all("img")) if data["body"] else 0
    img_counter = [0]

    def node(n) -> str:
        if isinstance(n, str):
            return n
        tag = n.name
        if not tag or tag in ["script", "style", "nav", "footer", "button", "svg"]:
            return ""

        ch = "".join(node(c) for c in n.children).strip()

        match tag:
            case "h1":          return f"\n\n# {ch}\n\n"
            case "h2":          return f"\n\n## {ch}\n\n"
            case "h3":          return f"\n\n### {ch}\n\n"
            case "h4":          return f"\n\n#### {ch}\n\n"
            case "p":           return f"\n\n{ch}\n\n" if ch else ""
            case "br":          return "\n"
            case "hr":          return "\n\n---\n\n"
            case "figure":      return f"\n\n{ch}\n\n"
            case "strong" | "b": return f"**{ch}**"
            case "em"     | "i": return f"*{ch}*"
            case "blockquote":
                return "\n\n" + "\n".join(f"> {l}" for l in ch.splitlines() if l.strip()) + "\n\n"
            case "code":
                return f"`{ch}`" if n.parent and n.parent.name != "pre" else ch
            case "pre":
                c    = n.find("code")
                lang = next((cl.replace("language-", "") for cl in (c.get("class") or []) if cl.startswith("language-")), "") if c else ""
                body = c.get_text() if c else n.get_text()
                return f"\n\n```{lang}\n{body}\n```\n\n"
            case "a":
                href = n.get("href", "")
                return f"[{ch}]({href})" if href and ch else ch
            case "img":
                src = n.get("src") or n.get("data-src") or n.get("data-lazy-src") or ""
                alt = n.get("alt", "image")
                if not src or src.startswith("data:"):
                    return ""
                if src.startswith("//"):
                    src = "https:" + src
                img_counter[0] += 1
                path = download_img(src, imgs_dir, img_counter[0], total_imgs) or src
                return f"\n\n![{alt}]({path})\n\n"
            case "ul":
                return "\n" + "\n".join(f"- {''.join(node(c) for c in li.children).strip()}" for li in n.find_all("li", recursive=False)) + "\n"
            case "ol":
                return "\n" + "\n".join(f"{i}. {''.join(node(c) for c in li.children).strip()}" for i, li in enumerate(n.find_all("li", recursive=False), 1)) + "\n"
            case _:
                return f"\n{ch}\n" if ch else ""

    if not data["body"]:
        return "No content found.", 0

    print(f"\n  {CYN}Downloading{R}  {GRY}{total_imgs} images{R}\n")

    raw = node(data["body"])
    if total_imgs:
        print()

    md = re.sub(r"\n{4,}", "\n\n\n", raw)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip(), img_counter[0]


def frontmatter(data: dict) -> str:
    tags = ", ".join(f'"{t}"' for t in data["tags"])
    return f'---\ntitle: "{data["title"].replace(chr(34), chr(39))}"\nauthor: "{data["author"]}"\ndate: "{data["date"]}"\nsource: "{data["url"]}"\ntags: [{tags}]\n---\n\n'


def scrape(url: str):
    data    = fetch(url)
    title   = data["title"] or "untitled"
    out_dir = Path("output") / sanitize(title)
    out_dir.mkdir(parents=True, exist_ok=True)

    md, img_count = to_markdown(data, out_dir)

    content = frontmatter(data) + f"# {title}\n\n" + md
    md_file = out_dir / "article.md"
    md_file.write_text(content, encoding="utf-8")

    print(f"\n  {GRN}Done{R}\n")
    divider()
    print(label("markdown", str(md_file)))
    print(label("images",   f"{img_count} saved  →  {out_dir / 'images'}"))
    print(label("size",     f"{len(content):,} chars"))
    divider()
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"\n  {YLW}Usage:{R}  python medium_scraper.py <url>\n")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        log_err("URL must start with http:// or https://")

    scrape(url)