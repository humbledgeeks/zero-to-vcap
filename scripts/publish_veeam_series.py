#!/usr/bin/env python3
"""Publish the Veeam "Zero to Protected" 5-part series to WordPress as drafts.

Distinct from the VCAP posts: this series lives in the infra-automation/veeam repo,
references local screenshots via ../images/... paths, and is filed under BOTH the
"Zero to VCAP" and a new "Zero to Protected" category with backup-relevant tags.

What it does per post:
  1. Uploads each referenced screenshot to the WP media library (cached; re-runs reuse).
  2. Builds clean Gutenberg blocks directly:
       - image + caption  -> wp:image figure with media id + <figcaption>
       - fenced code       -> wp:code with NO language attr (editor-safe)
       - headings/paras/tables/lists -> via publish.py's tested converter
  3. Creates a draft (or UPDATES the same draft on re-run) under both categories.
  4. Second pass: rewrites inter-post part-N-*.md links to the real draft URLs.

Run from the zero-to-vcap repo (so .env + venv resolve):
    source .venv/bin/activate
    python scripts/publish_veeam_series.py            # all 5
    python scripts/publish_veeam_series.py --only part-1-appliance-model-and-fabric.md
"""
import argparse
import base64
import html
import json
import os
import re
import sys
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv

# reuse the tested block converter + WP helpers from the sibling publisher
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish import (  # noqa: E402
    convert_to_gutenberg_blocks,
    build_wp_headers,
    upload_to_wp_media,
    resolve_or_create_tags,
    resolve_or_create_category,
    slugify,
)

SERIES_DIR = Path("/Users/ajohnson/_github/infra-automation/veeam/blog-series")
MEDIA_CACHE = SERIES_DIR / ".wp-media-veeam.json"
DRAFT_STATE = SERIES_DIR / ".wp-drafts-veeam.json"

CATEGORIES = ["Zero to VCAP", "Zero to Protected"]
BASE_TAGS = [
    "Veeam", "Veeam v13", "Backup", "Data Protection", "Immutability", "Ransomware",
    "VMware", "vSphere", "VVF", "vSAN", "Zero to Protected", "Zero to VCAP", "HumbledGeeks",
]
POSTS = [
    {"file": "part-1-appliance-model-and-fabric.md",
     "tags": ["Hardened Repository", "Linux Appliance", "MFA", "Rocky Linux"]},
    {"file": "part-2-assembling-the-infrastructure.md",
     "tags": ["Hardened Repository", "Scale-out Repository", "vCenter", "Certificate Pairing"]},
    {"file": "part-3-first-backup-and-immutability.md",
     "tags": ["Backup Job", "Application-Aware Processing", "Domain Controllers"]},
    {"file": "part-4-storage-integration-alletra.md",
     "tags": ["HPE Alletra", "Storage Snapshots", "iSCSI", "NVMe-TCP", "Backup Proxy"]},
    {"file": "part-5-guest-processing-linux.md",
     "tags": ["Application-Aware Processing", "Kerberos", "Active Directory", "Guest Processing"]},
]
FOCUS_KW = "Veeam v13 backup"

IMG_RE = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<path>\.\./images/[^)]+)\)'
    r'(?:\n\*(?P<cap>[^\n]+)\*)?'
)


def load_cfg():
    load_dotenv()
    wp = os.getenv("WORDPRESS_URL", "").rstrip("/")
    user = os.getenv("WORDPRESS_USERNAME", "")
    app = os.getenv("WORDPRESS_APP_PASSWORD", "")
    if not (wp and user and app):
        sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")
    return wp, build_wp_headers(user, app)


def inline_md(text):
    """Render a short inline span (bold/italic/code/links) and drop the wrapping <p>."""
    h = markdown.markdown(text.strip()).strip()
    return re.sub(r'^<p>(.*)</p>$', r'\1', h, flags=re.DOTALL)


def extract(md_text):
    """Return (title, body_with_placeholders, [ {alt, rel, cap} ...] in order)."""
    title_m = re.search(r'^#\s+(.+)', md_text, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else "Untitled"
    body = re.sub(r'^#\s+.+\n?', '', md_text, count=1, flags=re.MULTILINE).strip()

    images = []

    def repl(m):
        images.append({"alt": m.group("alt"), "rel": m.group("path"),
                       "cap": (m.group("cap") or "").strip()})
        return f"\n\n@@IMG{len(images) - 1}@@\n\n"

    body = IMG_RE.sub(repl, body)
    return title, body, images


def upload_images(images, post_path, wp, headers, cache):
    for img in images:
        rel = img["rel"]
        if rel in cache:
            continue
        abs_path = (post_path.parent / rel).resolve()
        if not abs_path.is_file():
            sys.exit(f"[error] image not found: {abs_path}")
        mid, url = upload_to_wp_media(abs_path.read_bytes(), abs_path.name, wp, headers)
        cache[rel] = {"id": mid, "url": url}
        MEDIA_CACHE.write_text(json.dumps(cache, indent=2))
        print(f"    uploaded {abs_path.name} -> {url}")


def image_block(img, cache):
    info = cache[img["rel"]]
    alt = html.escape(img["alt"], quote=True)
    cap = f'<figcaption class="wp-element-caption">{inline_md(img["cap"])}</figcaption>' if img["cap"] else ""
    return (
        f'<!-- wp:image {{"id":{info["id"]},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large">'
        f'<img src="{info["url"]}" alt="{alt}" class="wp-image-{info["id"]}"/>{cap}</figure>\n'
        f'<!-- /wp:image -->'
    )


def build_content(body, images, cache):
    html_body = markdown.markdown(body, extensions=["tables", "fenced_code"])
    blocks = convert_to_gutenberg_blocks(html_body)
    for n, img in enumerate(images):
        token = f"@@IMG{n}@@"
        block_re = re.compile(
            r'<!-- wp:paragraph -->\s*<p>' + re.escape(token) + r'</p>\s*<!-- /wp:paragraph -->'
        )
        fig = image_block(img, cache)
        blocks = block_re.sub(lambda m: fig, blocks, count=1)
    return blocks


def excerpt_from(blocks):
    for m in re.finditer(r'<p>(.*?)</p>', blocks, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) >= 140 and "·" not in text:
            return (text[:152].rsplit(" ", 1)[0] + "…") if len(text) > 155 else text
    return ""


def upsert(title, content, excerpt, cat_ids, tag_ids, wp, headers, post_id=None):
    jh = {**headers, "Content-Type": "application/json"}
    payload = {
        "title": title, "slug": slugify(title), "content": content, "excerpt": excerpt,
        "status": "draft", "categories": cat_ids, "tags": tag_ids,
        "meta": {"_yoast_wpseo_metadesc": excerpt, "_yoast_wpseo_focuskw": FOCUS_KW},
    }
    url = f"{wp}/wp-json/wp/v2/posts" + (f"/{post_id}" if post_id else "")
    r = requests.post(url, json=payload, headers=jh, timeout=60)
    r.raise_for_status()
    j = r.json()
    return j["id"], j["link"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="publish just one part-*.md filename")
    args = ap.parse_args()

    wp, headers = load_cfg()
    cache = json.loads(MEDIA_CACHE.read_text()) if MEDIA_CACHE.exists() else {}
    state = json.loads(DRAFT_STATE.read_text()) if DRAFT_STATE.exists() else {}

    print(f"Resolving categories {CATEGORIES} ...")
    cat_ids = [c for c in (resolve_or_create_category(n, wp, headers) for n in CATEGORIES) if c]

    posts = [p for p in POSTS if (not args.only or p["file"] == args.only)]
    prepared = []  # (fname, title, content) for the link-rewrite pass

    for p in posts:
        path = SERIES_DIR / p["file"]
        print(f"\n=== {p['file']} ===")
        title, body, images = extract(path.read_text(encoding="utf-8"))
        print(f"  {len(images)} images; title: {title}")
        upload_images(images, path, wp, headers, cache)
        content = build_content(body, images, cache)
        excerpt = excerpt_from(content)
        tag_ids = resolve_or_create_tags(BASE_TAGS + p["tags"], wp, headers)
        pid = state.get(p["file"], {}).get("id")
        pid, link = upsert(title, content, excerpt, cat_ids, tag_ids, wp, headers, post_id=pid)
        state[p["file"]] = {"id": pid, "link": link, "title": title}
        DRAFT_STATE.write_text(json.dumps(state, indent=2))
        prepared.append((p["file"], title, content))
        print(f"  {'updated' if p['file'] in state else 'created'} draft {pid} -> {link}")

    # second pass: rewrite inter-post links (part-N-*.md -> real draft URL)
    linkmap = {f: state[f]["link"] for f in state}
    print("\nRewriting inter-post links ...")
    for fname, title, content in prepared:
        new = content
        for target, url in linkmap.items():
            new = new.replace(f'href="{target}"', f'href="{url}"')
        if new != content:
            pid = state[fname]["id"]
            excerpt = excerpt_from(new)
            tag_ids = resolve_or_create_tags(
                BASE_TAGS + next(p["tags"] for p in POSTS if p["file"] == fname), wp, headers)
            upsert(title, new, excerpt, cat_ids, tag_ids, wp, headers, post_id=pid)
            print(f"  fixed links in {fname} (post {pid})")

    print("\n" + "=" * 60)
    for f, info in state.items():
        print(f"  {info['id']:>5}  {info['link']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
