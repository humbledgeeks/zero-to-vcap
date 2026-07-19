#!/usr/bin/env python3
"""Prepare the VCF 9.1 Lifecycle & Upgrades post for WordPress:
  1. Upload each referenced local screenshot to the WP media library (cached so re-runs reuse).
  2. Emit a publish-ready markdown copy: YAML front matter + HTML comments stripped,
     an H1 injected from the front-matter title (publish.py uses the H1 as the WP title),
     local image paths rewritten to their uploaded media URLs.
Then run:  python scripts/publish.py VCF-9.1-Lifecycle-Upgrades/_build-wp-draft.md --no-images --tags "..."

Modeled on vvf-vcenter-upgrade/build_wp_draft.py. TWO differences that matter:

  * LAYOUT. The VVF post kept its markdown and images/ in one directory and referenced
    them as images/<name>.jpg. Here the markdown lives in draft/ and references
    ../images/<NN-folder>/<name>.jpg, so refs are matched with a subfolder-aware regex
    and resolved against the post root rather than the markdown's own directory.

  * FILENAME COLLISIONS. Image basenames (upgrade_1.jpg, upgrade_6.jpg, ...) are reused
    across this post's section folders AND collide with the already-uploaded VVF post
    media. WordPress silently de-duplicates by appending -1/-2 to the slug, so the
    uploaded URL is NOT predictable from the basename. Cache keys are therefore the full
    relative path (images/NN-folder/name.jpg), and every rewrite uses the URL the API
    actually returned. Never reconstruct a media URL from a filename here.
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path("VCF-9.1-Lifecycle-Upgrades")
SRC = ROOT / "draft" / "zero-to-vcap-vcf91-lifecycle-upgrades.md"
BUILD = ROOT / "_build-wp-draft.md"
CACHE = ROOT / ".wp-media-vcf91-lifecycle-map.json"
IMG_ROOT = ROOT  # refs are ../images/NN/x.jpg from draft/, i.e. images/NN/x.jpg from ROOT

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
    "User-Agent": "zero-to-vcap-publisher/1.0",
}
CTYPE = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

raw = SRC.read_text(encoding="utf-8")

# pull the title out of the YAML front matter, then strip the front matter
title = None
if raw.startswith("---"):
    fm_end = raw.find("\n---", 3)
    fm = raw[3:fm_end]
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, flags=re.MULTILINE)
    if m:
        title = m.group(1).strip()
    raw = raw[fm_end + 4:]
if not title:
    sys.exit("[error] could not read title from front matter")

# strip HTML comments (ground-truth notes, IMAGE GAP note, DRAFT NOTES block)
raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

# publish.py uses the markdown H1 as the WP title; inject it
body = f"# {title}\n\n{raw.lstrip()}"

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

# refs look like ](../images/NN-folder/upgrade_X.jpg); capture the path minus the ../
REF = re.compile(r'\]\(\.\./(images/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\.(?:jpe?g|png))\)')
imgs = list(dict.fromkeys(REF.findall(body)))
if not imgs:
    sys.exit("[error] no ../images/<folder>/<file> refs found — check the path pattern")

missing = [r for r in imgs if not (IMG_ROOT / r).exists()]
if missing:
    sys.exit(f"[error] referenced images not found on disk: {missing}")

print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    p = IMG_ROOT / rel
    # upload under a section-qualified filename so the media library stays navigable and
    # collisions with other posts' upgrade_N.jpg are less likely to need WP's -1 suffix
    # The "-v2" generation marker exists because re-uploading after a redaction-policy
    # change reused the old filenames, so the URLs were identical and Cloudflare kept
    # serving the stale (redacted) images to readers. Bump this if the image CONTENT
    # ever changes again; a new URL cannot be served from a stale cache.
    fn = f"vcf91-lifecycle-v2-{Path(rel).parent.name}-{p.name}"
    ext = p.suffix.lower()
    data = p.read_bytes()
    h = {**HEADERS,
         "Content-Disposition": f'attachment; filename="{fn}"',
         "Content-Type": CTYPE.get(ext, "application/octet-stream")}
    r = requests.post(media_url, headers=h, data=data, timeout=120)
    r.raise_for_status()
    j = r.json()
    cache[rel] = {"id": j["id"], "url": j["source_url"]}
    CACHE.write_text(json.dumps(cache, indent=2))
    print(f"  [{i}/{len(imgs)}] uploaded {rel} -> {j['source_url']}")

# rewrite image paths -> uploaded URLs (match the ../ form used in the source)
out = body
for rel, info in cache.items():
    out = out.replace(f"](../{rel})", f"]({info['url']})")

leftover = REF.findall(out)
if leftover:
    sys.exit(f"[error] {len(leftover)} image refs were not rewritten: {leftover}")

BUILD.write_text(out, encoding="utf-8")
print(f"\nWrote {BUILD} (front matter stripped, H1 injected, {len(imgs)} image URLs rewritten).")
print("Next: python scripts/publish.py", BUILD, '--no-images --tags "..."')
