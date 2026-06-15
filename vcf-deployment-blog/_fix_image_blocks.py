#!/usr/bin/env python3
"""
Repair the malformed Gutenberg image blocks in WP post 1949.
publish.py emitted blocks without the media id and with class="wp-image"
(instead of wp-image-<id>), which triggers "Attempt Block Recovery".
This rewrites every wp:image block with the correct id + class. Post stays draft.
"""
import base64
import csv
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
MAP = REPO / "vcf-deployment-blog" / "wp-media-map.csv"
POST_ID = 1949

load_dotenv(REPO / ".env")
U = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
PW = os.getenv("WORDPRESS_APP_PASSWORD", "")
H = {"Authorization": "Basic " + base64.b64encode(f"{USER}:{PW}".encode()).decode(),
     "User-Agent": "zero-to-vcap-publisher/1.0"}

# base filename (no .jpg) -> media id
key2id = {}
with MAP.open() as f:
    for row in csv.DictReader(f):
        key2id[Path(row["filename"]).stem] = int(row["media_id"])


def src_key(src):
    name = Path(src).name
    name = re.sub(r"\.(jpe?g|png)$", "", name, flags=re.I)
    name = re.sub(r"-scaled$", "", name)
    return name


BLOCK = re.compile(
    r'<!-- wp:image \{[^}]*\} -->\s*'
    r'<figure class="wp-block-image size-large">'
    r'<img (?P<imgattrs>[^>]*?)\s*/?>'
    r'</figure>\s*'
    r'<!-- /wp:image -->',
    re.DOTALL,
)

fixed = 0
missing = []


def repl(m):
    global fixed
    attrs = m.group("imgattrs")
    src = re.search(r'src="([^"]+)"', attrs).group(1)
    alt_m = re.search(r'alt="([^"]*)"', attrs)
    alt = alt_m.group(1) if alt_m else ""
    key = src_key(src)
    mid = key2id.get(key)
    if not mid:
        missing.append(key)
        return m.group(0)
    fixed += 1
    return (
        f'<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large">'
        f'<img src="{src}" alt="{alt}" class="wp-image-{mid}"/>'
        f'</figure>\n'
        f'<!-- /wp:image -->'
    )


content = requests.get(f"{U}/wp-json/wp/v2/posts/{POST_ID}?context=edit",
                       headers=H, timeout=30).json()["content"]["raw"]
new = BLOCK.sub(repl, content)
print(f"Fixed {fixed} image blocks. Missing ids: {missing or 'none'}")
if fixed != 71:
    sys.exit(f"[abort] expected 71, fixed {fixed} — not updating post")

r = requests.post(f"{U}/wp-json/wp/v2/posts/{POST_ID}",
                  headers={**H, "Content-Type": "application/json"},
                  json={"content": new}, timeout=60)
r.raise_for_status()
print("Updated post status:", r.json()["status"])
