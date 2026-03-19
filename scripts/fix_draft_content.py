#!/usr/bin/env python3
"""
fix_draft_content.py
Re-parse the blog post with the fixed Gutenberg converter and PATCH the
existing WordPress draft (post 1794) with corrected content.

Run from the zero-to-vcap repo root:
    python3 scripts/fix_draft_content.py
"""

import base64
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------

REPO_ROOT     = Path(__file__).parent.parent
BLOG_POST     = REPO_ROOT / "blog-posts/flexpod-vcf-ucs-foundation.md"
POST_ID       = 1794

load_dotenv(REPO_ROOT / ".env")
WP_URL      = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER     = os.getenv("WORDPRESS_USERNAME", "")
WP_APP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")

token = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}",
    "Content-Type": "application/json",
    "User-Agent": "zero-to-vcap-publisher/1.0",
}

# ---------------------------------------------------------------------------
# Fixed Gutenberg converter (same as publish.py but with image + code fixes)
# ---------------------------------------------------------------------------

import markdown as md_lib


def _convert_list_items(list_html):
    items = re.findall(r'<li>(.*?)</li>', list_html, re.DOTALL)
    result = ''
    for item in items:
        result += f'<!-- wp:list-item -->\n<li>{item.strip()}</li>\n<!-- /wp:list-item -->\n'
    return result


def convert_to_gutenberg_blocks(html):
    blocks = []
    pattern = re.compile(
        r'(<table>.*?</table>)'
        r'|(<blockquote>.*?</blockquote>)'
        r'|(<pre[^>]*>.*?</pre>)'
        r'|(<ul>.*?</ul>)'
        r'|(<ol>.*?</ol>)'
        r'|(<h2[^>]*>.*?</h2>)'
        r'|(<h3[^>]*>.*?</h3>)'
        r'|(<p>.*?</p>)',
        re.DOTALL,
    )

    for match in pattern.finditer(html):
        element = match.group(0)

        if element.startswith('<table>'):
            blocks.append(
                f'<!-- wp:table -->\n'
                f'<figure class="wp-block-table">{element}</figure>\n'
                f'<!-- /wp:table -->'
            )

        elif element.startswith('<blockquote>'):
            inner = re.search(r'<blockquote>(.*?)</blockquote>', element, re.DOTALL)
            inner_html = inner.group(1).strip() if inner else ''
            blocks.append(
                f'<!-- wp:quote -->\n'
                f'<blockquote class="wp-block-quote">{inner_html}</blockquote>\n'
                f'<!-- /wp:quote -->'
            )

        elif element.startswith('<pre'):
            # Fenced code block — preserve language for Prism.js syntax highlighting.
            # Python markdown fenced_code emits: <pre><code class="language-powershell">…</code></pre>
            code_match = re.search(r'<code([^>]*)>(.*?)</code>', element, re.DOTALL)
            if code_match:
                code_attrs    = code_match.group(1)
                code_content  = code_match.group(2)
                lang_m        = re.search(r'class=["\'](?:language-)?(\w+)["\']', code_attrs)
                lang          = lang_m.group(1).lower() if lang_m else None
            else:
                code_content = element
                lang         = None

            if lang:
                lang_class = f'language-{lang}'
                blocks.append(
                    f'<!-- wp:code {{"className":"{lang_class}"}} -->\n'
                    f'<pre class="wp-block-code {lang_class}"><code class="{lang_class}">{code_content}</code></pre>\n'
                    f'<!-- /wp:code -->'
                )
            else:
                blocks.append(
                    f'<!-- wp:code -->\n'
                    f'<pre class="wp-block-code"><code>{code_content}</code></pre>\n'
                    f'<!-- /wp:code -->'
                )

        elif element.startswith('<ul>'):
            items_html = _convert_list_items(element)
            blocks.append(
                f'<!-- wp:list -->\n'
                f'<ul class="wp-block-list">{items_html}</ul>\n'
                f'<!-- /wp:list -->'
            )

        elif element.startswith('<ol>'):
            items_html = _convert_list_items(element)
            blocks.append(
                f'<!-- wp:list {{"ordered":true}} -->\n'
                f'<ol class="wp-block-list">{items_html}</ol>\n'
                f'<!-- /wp:list -->'
            )

        elif re.match(r'<h2', element):
            inner = re.search(r'<h2[^>]*>(.*?)</h2>', element, re.DOTALL).group(1)
            blocks.append(
                f'<!-- wp:heading {{"level":2}} -->\n'
                f'<h2 class="wp-block-heading">{inner}</h2>\n'
                f'<!-- /wp:heading -->'
            )

        elif re.match(r'<h3', element):
            inner = re.search(r'<h3[^>]*>(.*?)</h3>', element, re.DOTALL).group(1)
            blocks.append(
                f'<!-- wp:heading {{"level":3}} -->\n'
                f'<h3 class="wp-block-heading">{inner}</h3>\n'
                f'<!-- /wp:heading -->'
            )

        elif element.startswith('<p>'):
            # Paragraph containing ONLY an image → proper wp:image block
            img_only = re.match(r'^<p>\s*<img ([^>]+?)/?>\s*</p>$', element, re.DOTALL)
            if img_only:
                attrs = img_only.group(1)
                src_m = re.search(r'src="([^"]+)"', attrs)
                alt_m = re.search(r'alt="([^"]*)"', attrs)
                src = src_m.group(1) if src_m else ''
                alt = alt_m.group(1) if alt_m else ''
                blocks.append(
                    f'<!-- wp:image {{"sizeSlug":"large","linkDestination":"none"}} -->\n'
                    f'<figure class="wp-block-image size-large">'
                    f'<img src="{src}" alt="{alt}" class="wp-image"/>'
                    f'</figure>\n'
                    f'<!-- /wp:image -->'
                )
            else:
                blocks.append(
                    f'<!-- wp:paragraph -->\n'
                    f'{element}\n'
                    f'<!-- /wp:paragraph -->'
                )

    return '\n\n'.join(blocks)


def parse_markdown(filepath):
    raw = Path(filepath).read_text(encoding="utf-8")
    title_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(filepath).stem
    body_md = re.sub(r'^#\s+.+\n?', '', raw, count=1, flags=re.MULTILINE).strip()
    # Remove frontmatter-style tags line if present
    body_md = re.sub(r'^\*Tags:.*?\*\s*\n?', '', body_md, flags=re.MULTILINE).strip()
    converter = md_lib.Markdown(extensions=["tables", "fenced_code", "nl2br"])
    body_html = convert_to_gutenberg_blocks(converter.convert(body_md))
    return title, body_html


def extract_excerpt(body_html, max_chars=155):
    match = re.search(r'<p>(.*?)</p>', body_html, re.DOTALL)
    if not match:
        return ""
    text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(' ', 1)[0] + "…"
    return text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nParsing: {BLOG_POST}")
    title, body_html = parse_markdown(BLOG_POST)
    excerpt = extract_excerpt(body_html)

    # Verify block counts
    images    = len(re.findall(r'<!-- wp:image', body_html))
    code      = len(re.findall(r'<!-- wp:code', body_html))
    headings  = len(re.findall(r'<!-- wp:heading', body_html))
    tables    = len(re.findall(r'<!-- wp:table', body_html))
    paragraphs = len(re.findall(r'<!-- wp:paragraph', body_html))

    print(f"  Title      : {title}")
    print(f"  Excerpt    : {excerpt[:80]}...")
    print(f"  Images     : {images}")
    print(f"  Code blocks: {code}")
    print(f"  Headings   : {headings}")
    print(f"  Tables     : {tables}")
    print(f"  Paragraphs : {paragraphs}")

    if images == 0:
        print("\n[warn] No image blocks found — check markdown image syntax.")
    if code == 0:
        print("\n[warn] No code blocks found — check fenced code blocks in markdown.")

    print(f"\nPatching post {POST_ID} on {WP_URL} ...")
    url = f"{WP_URL}/wp-json/wp/v2/posts/{POST_ID}"
    payload = {
        "title":   title,
        "content": body_html,
        "excerpt": excerpt,
    }
    resp = requests.post(url, json=payload, headers=HEADERS, timeout=30)
    if not resp.ok:
        print(f"[error] HTTP {resp.status_code}: {resp.text[:400]}")
        sys.exit(1)

    data = resp.json()
    print(f"\n{'='*55}")
    print(f"  Done! Draft updated.")
    print(f"  Post ID : {data.get('id')}")
    print(f"  Preview : {data.get('link')}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
