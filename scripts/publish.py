#!/usr/bin/env python3
"""
publish.py — Zero to VCAP Blog Publisher
Converts a Markdown blog post to a WordPress draft with AI-generated images.

Usage:
    python scripts/publish.py blog-posts/my-post.md
    python scripts/publish.py blog-posts/my-post.md --no-images
"""

import argparse
import base64
import os
import re
import sys
import time
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


# ---------------------------------------------------------------------------
# Config & Auth
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Publish a Markdown blog post to WordPress with AI-generated images."
    )
    parser.add_argument("filepath", help="Path to the Markdown file to publish")
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image generation and publish text-only draft",
    )
    return parser.parse_args()


def load_config():
    load_dotenv()
    required = [
        "WORDPRESS_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APP_PASSWORD",
        "OPENAI_API_KEY",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        print(f"[error] Missing required environment variables: {', '.join(missing)}")
        print("        Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    return {key: os.getenv(key) for key in required}


def build_wp_headers(username, app_password):
    token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "User-Agent": "zero-to-vcap-publisher/1.0",
    }


# ---------------------------------------------------------------------------
# Markdown Parsing + Gutenberg Conversion
# ---------------------------------------------------------------------------

def _convert_list_items(list_html):
    """Wrap <li> items in Gutenberg list-item blocks."""
    items = re.findall(r'<li>(.*?)</li>', list_html, re.DOTALL)
    result = ''
    for item in items:
        result += f'<!-- wp:list-item -->\n<li>{item.strip()}</li>\n<!-- /wp:list-item -->\n'
    return result


def convert_to_gutenberg_blocks(html):
    """Convert plain HTML to WordPress Gutenberg block markup."""
    blocks = []
    pattern = re.compile(
        r'(<table>.*?</table>)'
        r'|(<blockquote>.*?</blockquote>)'
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
            blocks.append(
                f'<!-- wp:paragraph -->\n'
                f'{element}\n'
                f'<!-- /wp:paragraph -->'
            )

    return '\n\n'.join(blocks)


def parse_markdown(filepath):
    raw = Path(filepath).read_text(encoding="utf-8")

    # Extract H1 as post title
    title_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(filepath).stem

    # Remove H1 from body (WordPress handles title separately)
    body_md = re.sub(r'^#\s+.+\n?', '', raw, count=1, flags=re.MULTILINE).strip()

    # Convert Markdown to HTML then to Gutenberg blocks
    md = markdown.Markdown(extensions=["tables", "fenced_code", "nl2br"])
    body_html = convert_to_gutenberg_blocks(md.convert(body_md))

    # Collect H2 headings for image placement
    h2_sections = re.findall(r'^##\s+(.+)', body_md, re.MULTILINE)

    return title, body_html, h2_sections


# ---------------------------------------------------------------------------
# Image Generation
# ---------------------------------------------------------------------------

BASE_STYLE = (
    "Clean enterprise IT illustration, dark blue and gray color palette, "
    "subtle datacenter or cloud infrastructure elements, modern flat design with "
    "slight depth. No text, no logos, no people, no brand marks."
)


def build_featured_prompt(title):
    return (
        f"Professional technology blog header image for an article titled: '{title}'. "
        f"{BASE_STYLE} Widescreen 16:9 format."
    )


def build_inline_prompt(heading, title):
    return (
        f"Technical illustration for a blog section titled '{heading}' "
        f"within an article about '{title}'. "
        f"{BASE_STYLE} Abstract server infrastructure, software-defined networking, "
        "or private cloud architecture concepts. Widescreen 16:9 format."
    )


def _download_image(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def generate_featured_image(title, api_key):
    client = OpenAI(api_key=api_key)
    prompt = build_featured_prompt(title)
    try:
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
        )
    except OpenAIError as e:
        print(f"[error] OpenAI image generation failed: {e}")
        sys.exit(1)

    image_bytes = _download_image(result.data[0].url)
    filename = "featured-image.png"
    return image_bytes, filename


def generate_inline_image(heading, title, api_key):
    client = OpenAI(api_key=api_key)
    prompt = build_inline_prompt(heading, title)
    try:
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
    except OpenAIError as e:
        print(f"[error] OpenAI image generation failed for '{heading}': {e}")
        sys.exit(1)

    safe_name = re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')
    image_bytes = _download_image(result.data[0].url)
    filename = f"inline-{safe_name}.png"
    return image_bytes, filename


# ---------------------------------------------------------------------------
# Image Placement Selection
# ---------------------------------------------------------------------------

def select_sections_for_images(h2_sections, max_images=3):
    if not h2_sections:
        return []
    # Skip the last H2 (typically a wrap-up or progress tracker)
    candidates = h2_sections[:-1] if len(h2_sections) > 1 else h2_sections
    if not candidates:
        return []
    # Distribute evenly across candidates
    step = max(1, len(candidates) // max_images)
    return candidates[::step][:max_images]


# ---------------------------------------------------------------------------
# WordPress API
# ---------------------------------------------------------------------------

def upload_to_wp_media(image_bytes, filename, wp_url, wp_headers):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"
    headers = {
        **wp_headers,
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "image/png",
    }
    try:
        response = requests.post(url, headers=headers, data=image_bytes, timeout=60)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"[error] WordPress media upload failed: {e}")
        print(f"        Response: {response.text[:500]}")
        sys.exit(1)
    data = response.json()
    return data["id"], data["source_url"]


def insert_inline_images(body_html, inline_image_map):
    for heading, media_url in inline_image_map.items():
        img_block = (
            f'\n\n<!-- wp:image {{"sizeSlug":"large"}} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<img src="{media_url}" alt="{heading}"/>'
            f'</figure>\n'
            f'<!-- /wp:image -->'
        )
        # Match the Gutenberg h2 block for this heading
        pattern = re.compile(
            r'(<!-- wp:heading \{"level":2\} -->\n'
            r'<h2 class="wp-block-heading">'
            + re.escape(heading)
            + r'</h2>\n<!-- /wp:heading -->)',
            re.IGNORECASE,
        )
        body_html = pattern.sub(r'\1' + img_block, body_html, count=1)
    return body_html


def create_wp_draft(title, html_content, featured_media_id, wp_url, wp_headers):
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    headers = {**wp_headers, "Content-Type": "application/json"}
    payload = {
        "title": title,
        "content": html_content,
        "status": "draft",
        "featured_media": featured_media_id,
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"[error] WordPress post creation failed: {e}")
        print(f"        Response: {response.text[:500]}")
        sys.exit(1)
    data = response.json()
    return data["id"], data["link"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    config = load_config()

    filepath = Path(args.filepath)
    if not filepath.exists():
        print(f"[error] File not found: {filepath}")
        sys.exit(1)

    wp_headers = build_wp_headers(
        config["WORDPRESS_USERNAME"],
        config["WORDPRESS_APP_PASSWORD"],
    )

    # --- Parse Markdown ---
    print(f"\nParsing: {filepath}")
    title, body_html, h2_sections = parse_markdown(filepath)
    print(f"  Title    : {title}")
    print(f"  Sections : {h2_sections}")

    featured_id = 0
    final_html = body_html

    if args.no_images:
        print("\nSkipping image generation (--no-images)")
    else:
        # --- Featured Image ---
        print("\nGenerating featured image (DALL-E 3 HD)...")
        featured_bytes, featured_filename = generate_featured_image(
            title, config["OPENAI_API_KEY"]
        )
        print("  Uploading featured image to WordPress...")
        featured_id, featured_url = upload_to_wp_media(
            featured_bytes, featured_filename,
            config["WORDPRESS_URL"], wp_headers,
        )
        print(f"  Uploaded : {featured_url}")

        # --- Inline Images ---
        selected_sections = select_sections_for_images(h2_sections, max_images=3)
        inline_image_map = {}

        for section in selected_sections:
            print(f"\nGenerating inline image for: {section}")
            time.sleep(2)  # Stay within DALL-E rate limits
            img_bytes, img_filename = generate_inline_image(
                section, title, config["OPENAI_API_KEY"]
            )
            print(f"  Uploading inline image...")
            _, media_url = upload_to_wp_media(
                img_bytes, img_filename,
                config["WORDPRESS_URL"], wp_headers,
            )
            inline_image_map[section] = media_url
            print(f"  Uploaded : {media_url}")

        # --- Inject Images Into HTML ---
        final_html = insert_inline_images(body_html, inline_image_map)

    # --- Create WordPress Draft ---
    print("\nCreating WordPress draft...")
    post_id, post_link = create_wp_draft(
        title, final_html, featured_id,
        config["WORDPRESS_URL"], wp_headers,
    )

    print("\n" + "=" * 50)
    print("  Done!")
    print(f"  Post ID  : {post_id}")
    print(f"  Preview  : {post_link}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
