#!/usr/bin/env python3
"""Post-process a published WordPress draft for the Workload Domain post:
  1. Convert Tip/Gotcha wp:quote blocks into styled colored callout boxes
     (orange/tan for Gotcha-style warnings, blue for Tip-style notes).
  2. Patch wp:image blocks with their media IDs + wp-image-<id> class and make
     them clickable (linkDestination: media), using the upload cache.

Re-run this after any `publish.py --post-id` refresh (that regenerates content
from markdown, resetting quotes to plain wp:quote and images to linkDestination
none). Idempotent: already-styled blocks won't re-match.

Usage:  .venv/bin/python vcf-deployment-wld/style_draft.py <post_id>
"""
import os, sys, base64, json, re, requests
from pathlib import Path
from dotenv import load_dotenv

POST_ID = sys.argv[1] if len(sys.argv) > 1 else "2071"
CACHE = Path("vcf-deployment-wld/.wp-media-map.json")

load_dotenv(dotenv_path=".env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
U = os.getenv("WORDPRESS_USERNAME", "")
A = os.getenv("WORDPRESS_APP_PASSWORD", "")
H = {"Authorization": "Basic " + base64.b64encode(f"{U}:{A}".encode()).decode()}

# Callout palette (matched to the sample: tan/orange warning, light-blue note)
GOTCHA = {"bg": "#FBEFD8", "border": "#C77E1B", "label": "#B5670F"}
TIP    = {"bg": "#E4EEF7", "border": "#2E6DB4", "label": "#1A5FB4"}

url2id = {v["url"]: v["id"] for v in json.load(open(CACHE)).values()}

c = requests.get(f"{WP}/wp-json/wp/v2/posts/{POST_ID}?context=edit", headers=H, timeout=60).json()["content"]["raw"]

# --- 1. Tip/Gotcha quote blocks -> styled callout boxes ---
quote = re.compile(
    r'<!-- wp:quote -->\n<blockquote class="wp-block-quote">(.*?)</blockquote>\n<!-- /wp:quote -->',
    re.DOTALL)

callouts = [0]
def _box(para):
    """Render one callout paragraph as a styled box, colored by its own label."""
    label = re.search(r'<strong>(.*?)</strong>', para, re.DOTALL)
    label_txt = (label.group(1) if label else "").strip().lower()
    palette = GOTCHA if label_txt.startswith("gotcha") else TIP
    # recolor the first <strong> (the Tip:/Gotcha: label)
    para = re.sub(r'<strong>', f'<strong style="color:{palette["label"]};">', para, count=1)
    callouts[0] += 1
    return (f'<!-- wp:html -->\n'
            f'<div style="background:{palette["bg"]};border-left:5px solid {palette["border"]};'
            f'padding:14px 18px;margin:18px 0;border-radius:4px;">{para}</div>\n'
            f'<!-- /wp:html -->')

def style_quote(m):
    inner = m.group(1)
    # Python-Markdown merges adjacent blockquotes — split back into one box per paragraph.
    paras = re.findall(r'<p>.*?</p>', inner, re.DOTALL) or [inner]
    return '\n\n'.join(_box(p) for p in paras)

c = quote.sub(style_quote, c)

# --- 2. image blocks -> media IDs + clickable ---
imgblock = re.compile(
    r'<!-- wp:image \{"sizeSlug":"large","linkDestination":"none"\} -->\n'
    r'<figure class="wp-block-image size-large"><img src="([^"]+)" alt="([^"]*)"/></figure>\n'
    r'<!-- /wp:image -->')

imgs = [0]
def style_img(m):
    src, alt = m.group(1), m.group(2)
    mid = url2id.get(src)
    if not mid:
        return m.group(0)
    imgs[0] += 1
    return (f'<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"media"}} -->\n'
            f'<figure class="wp-block-image size-large"><a href="{src}">'
            f'<img src="{src}" alt="{alt}" class="wp-image-{mid}"/></a></figure>\n'
            f'<!-- /wp:image -->')

c = imgblock.sub(style_img, c)

r = requests.post(f"{WP}/wp-json/wp/v2/posts/{POST_ID}",
                  headers={**H, "Content-Type": "application/json"},
                  data=json.dumps({"content": c}), timeout=120)
r.raise_for_status()
print(f"callout boxes styled : {callouts[0]}")
print(f"image blocks patched : {imgs[0]}")

# verify
c2 = requests.get(f"{WP}/wp-json/wp/v2/posts/{POST_ID}?context=edit", headers=H, timeout=60).json()["content"]["raw"]
print("  border-left callouts :", c2.count("border-left:5px"))
print("  wp-image-<id> classes:", len(re.findall(r'class="wp-image-\d+"', c2)))
print("  leftover plain quotes:", c2.count("<!-- wp:quote -->"))
print("  leftover img none    :", c2.count('"linkDestination":"none"'))
