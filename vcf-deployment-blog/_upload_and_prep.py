#!/usr/bin/env python3
"""
Upload the 71 VCF 9.1 deployment screenshots (JPG) to WordPress media, then
emit a publish-ready copy of the blog post with local image paths swapped for
WordPress media URLs. Records each upload's media ID + URL to wp-media-map.csv
so the uploads can be deleted later if the draft is rejected.

Run from repo root:  .venv/bin/python vcf-deployment-blog/_upload_and_prep.py
Then:                .venv/bin/python scripts/publish.py <printed path> --no-images --tags "..."
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
IMG_DIR = REPO / "vcf-deployment-blog"
BLOG = REPO / "blog-posts" / "zero-to-vcap-vcf91-deployment.md"
OUT_MD = IMG_DIR / "_vcf91-publish.md"
MEDIA_MAP = IMG_DIR / "wp-media-map.csv"

load_dotenv(REPO / ".env")
WP_URL = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER = os.getenv("WORDPRESS_USERNAME", "")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not all([WP_URL, WP_USER, WP_PASS]):
    sys.exit("[error] Missing WordPress credentials in .env")

token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {"Authorization": f"Basic {token}", "User-Agent": "zero-to-vcap-publisher/1.0"}


def upload(path: Path):
    url = f"{WP_URL}/wp-json/wp/v2/media"
    headers = {
        **HEADERS,
        "Content-Disposition": f'attachment; filename="{path.name}"',
        "Content-Type": "image/jpeg",
    }
    resp = requests.post(url, headers=headers, data=path.read_bytes(), timeout=120)
    resp.raise_for_status()
    j = resp.json()
    return j["id"], j["source_url"]


def main():
    images = sorted(IMG_DIR.glob("vcf-9-1-deploy-*.jpg"))
    if len(images) != 71:
        sys.exit(f"[error] expected 71 images, found {len(images)}")
    print(f"Uploading {len(images)} images to {WP_URL} ...\n")

    url_map = {}
    rows = []
    for i, img in enumerate(images, 1):
        mid, src = upload(img)
        url_map[img.name] = src
        rows.append((img.name, mid, src))
        print(f"  [{i:2}/71] {img.name}  ->  id {mid}")

    with MEDIA_MAP.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "media_id", "url"])
        w.writerows(rows)
    print(f"\nWrote media map: {MEDIA_MAP.name}")

    # Rewrite blog md: ![alt](../vcf-deployment-blog/NAME.jpg) -> ![alt](wp_url)
    content = BLOG.read_text(encoding="utf-8")
    n = 0

    def repl(m):
        nonlocal n
        alt, path = m.group(1), m.group(2)
        fname = Path(path).name
        if fname in url_map:
            n += 1
            return f"![{alt}]({url_map[fname]})"
        print(f"  [warn] no WP URL for {fname}")
        return m.group(0)

    modified = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, content)
    OUT_MD.write_text(modified, encoding="utf-8")
    print(f"Wrote publish-ready markdown: {OUT_MD}")
    print(f"  {n}/71 image paths swapped to WordPress URLs.")
    if n != 71:
        sys.exit("[error] not all images were swapped — check warnings above")
    print(f"\nNext: .venv/bin/python scripts/publish.py {OUT_MD}")


if __name__ == "__main__":
    main()
