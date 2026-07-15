#!/usr/bin/env python3
"""Re-apply the WordPress draft fixes that `scripts/publish.py` can't produce itself.

publish.py regenerates a post's content from markdown on every `--post-id` run, so
these three Gutenberg corrections must be re-applied after each publish:

  1. wp:image blocks  -> add the media `id` + `wp-image-<id>` class (canonical
     core/image; otherwise the editor shows "Attempt Block Recovery").
  2. wp:code blocks   -> strip the invalid `{"language":...}` attribute and the
     `<code class="language-...">` class (core/code has no language attribute).
     Highlighting still works: the Astra-child Prism script re-adds the class at runtime.
  3. DRAFT NOTES      -> re-inject the source's `<!-- DRAFT NOTES -->` block as a
     Custom HTML (wp:html) block (publish.py drops raw HTML comments).

Idempotent — safe to run repeatedly. Usage:
  python vcf-license/postprocess_wp.py <post_id> [--cache PATH] [--src PATH]

Defaults target the AD-SSO post. For other posts pass --cache (the build media map)
and --src (the source markdown, only needed if it carries a DRAFT NOTES comment).
"""
import argparse, base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

ap = argparse.ArgumentParser()
ap.add_argument("post_id", type=int)
ap.add_argument("--cache", default="vcf-license/.wp-media-ad-sso-map.json",
                help="build media map JSON ({rel: {id, url}}); enables the image fix")
ap.add_argument("--src", default="vcf-license/vcf-active-directory-sso.md",
                help="source markdown; its <!-- DRAFT NOTES --> block is re-injected if present")
args = ap.parse_args()

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")
H = {"Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
     "User-Agent": "zero-to-vcap-publisher/1.0"}
PID = args.post_id
URL = f"{WP}/wp-json/wp/v2/posts/{PID}"

content = requests.get(URL, headers=H, params={"context": "edit"}, timeout=60).json()["content"]["raw"]
orig = content

# 1. images -> canonical core/image with id + wp-image-<id> class
url2id, unmatched = {}, []
cache_path = Path(args.cache)
if cache_path.exists():
    url2id = {v["url"]: v["id"] for v in json.loads(cache_path.read_text()).values()}
    def fix_img(m):
        block = m.group(0)
        s = re.search(r'src="([^"]+)"', block)
        if not s:
            return block
        src = s.group(1); mid = url2id.get(src)
        if not mid:
            unmatched.append(src); return block
        a = re.search(r'alt="([^"]*)"', block); alt = a.group(1) if a else ""
        return (f'<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"none"}} -->\n'
                f'<figure class="wp-block-image size-large">'
                f'<img src="{src}" alt="{alt}" class="wp-image-{mid}"/></figure>\n'
                f'<!-- /wp:image -->')
    content = re.sub(r'<!-- wp:image .*?<!-- /wp:image -->', fix_img, content, flags=re.DOTALL)
else:
    print(f"[warn] cache {cache_path} not found — skipping image id fix")

# 2. code -> drop the unsupported language attribute and <code> class
content = re.sub(r'<!-- wp:code \{"language":"[^"]+"\} -->', '<!-- wp:code -->', content)
content = re.sub(r'<code class="language-[^"]+">', '<code>', content)

# 3. re-inject DRAFT NOTES as a wp:html block if the source has one and it's missing
src_path = Path(args.src)
if src_path.exists() and "DRAFT NOTES" not in content:
    m = re.search(r"<!--\s*DRAFT NOTES.*?-->", src_path.read_text(), re.DOTALL)
    if m:
        content += f"\n\n<!-- wp:html -->\n{m.group(0)}\n<!-- /wp:html -->"

img_fixed = len(re.findall(r'<!-- wp:image \{"id":\d+', content))
img_total = content.count("<!-- wp:image")
code_total = content.count("<!-- wp:code")
print(f"images canonical : {img_fixed}/{img_total}" + (f"  (unmatched: {len(unmatched)})" if unmatched else ""))
print(f"code blocks      : {code_total} (language attrs left: {len(re.findall(chr(60)+'!-- wp:code .language', content))})")
print(f"code <code> class: {len(re.findall(r'<code class=.language-', content))} left")
print(f"draft-notes      : {'present' if 'DRAFT NOTES' in content else 'absent'}")
if unmatched:
    print("[warn] image srcs not in cache (left as-is):")
    for u in unmatched:
        print("   ", u)

if content == orig:
    print("no changes needed — already clean.")
else:
    r = requests.post(URL, headers={**H, "Content-Type": "application/json"},
                      json={"content": content}, timeout=60)
    r.raise_for_status()
    print(f"patched post {PID}.")
