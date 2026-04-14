#!/usr/bin/env python3
"""
WordPress Draft Upload — Push generated blog articles to WordPress via REST API.

Takes a generated HTML article + images directory and creates a WordPress draft
with all RankMath SEO fields populated.

Usage:
    python scripts/wordpress_upload.py output/article.html
    python scripts/wordpress_upload.py output/article.html --images output/images
    python scripts/wordpress_upload.py output/article.html --dry-run

Environment variables (in .env):
    WORDPRESS_URL           https://wordpress-1171553-6117772.cloudwaysapps.com
    WORDPRESS_USERNAME      your-username
    WORDPRESS_APP_PASSWORD  xxxx xxxx xxxx xxxx xxxx xxxx

Dependencies:
    pip install requests beautifulsoup4
"""

import argparse
import base64
import datetime
import html as html_module
import json
import os
import re
import sys
import time
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: 'beautifulsoup4' package required. Install with: pip install beautifulsoup4")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FILLER_WORDS = {
    "the", "a", "an", "for", "with", "and", "how", "to", "in", "on", "of",
    "is", "are", "your", "my", "our", "this", "that", "its", "does", "do",
    "can", "will", "what", "why", "when", "where", "which", "who",
}

CONTENT_TYPE_MAP = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".avif": "image/avif",
}

# Schema / site defaults
SITE_NAME = "Green Energy Thailand"
SITE_LOGO_PATH = "/wp-content/uploads/logo.png"
SITE_LOGO_WIDTH = 300
SITE_LOGO_HEIGHT = 60
AUTHOR_NAME = "Green Energy Thailand"


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------

def load_env(env_path: Path) -> dict:
    """Load .env file into a dict (simple key=value parser)."""
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def get_wp_config() -> tuple[str, str, str]:
    """Return (url, username, app_password) from env, or exit with error."""
    # Try .env file first, then environment variables
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env = load_env(env_path)

    url = os.environ.get("WORDPRESS_URL") or env.get("WORDPRESS_URL", "")
    username = os.environ.get("WORDPRESS_USERNAME") or env.get("WORDPRESS_USERNAME", "")
    app_password = os.environ.get("WORDPRESS_APP_PASSWORD") or env.get("WORDPRESS_APP_PASSWORD", "")

    missing = []
    if not url:
        missing.append("WORDPRESS_URL")
    if not username:
        missing.append("WORDPRESS_USERNAME")
    if not app_password:
        missing.append("WORDPRESS_APP_PASSWORD")

    if missing:
        print(f"Error: Missing WordPress credentials: {', '.join(missing)}")
        print("Set them in .env or as environment variables.")
        sys.exit(1)

    # Strip trailing slash from URL
    url = url.rstrip("/")
    # Strip spaces from app password before encoding (WordPress generates with spaces)
    app_password = app_password.replace(" ", "")

    return url, username, app_password


def make_auth_header(username: str, app_password: str) -> dict:
    """Build Basic Auth header from username and application password."""
    token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ---------------------------------------------------------------------------
# HTML Parsing
# ---------------------------------------------------------------------------

def parse_article(html_path: Path) -> dict:
    """Extract metadata and content from a generated HTML article."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    meta = {}

    # Title
    title_tag = soup.find("title")
    meta["title"] = title_tag.get_text(strip=True) if title_tag else ""

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    meta["description"] = desc_tag["content"] if desc_tag and desc_tag.get("content") else ""

    # OG tags
    for prop in ["og:title", "og:description", "og:image", "og:type"]:
        tag = soup.find("meta", attrs={"property": prop})
        key = prop.replace("og:", "og_")
        meta[key] = tag["content"] if tag and tag.get("content") else ""

    # Twitter card
    twitter_tag = soup.find("meta", attrs={"name": "twitter:card"})
    meta["twitter_card"] = twitter_tag["content"] if twitter_tag and twitter_tag.get("content") else "summary_large_image"

    # Author
    author_tag = soup.find("meta", attrs={"name": "author"})
    meta["author"] = author_tag["content"] if author_tag and author_tag.get("content") else ""

    # Date
    date_tag = soup.find("meta", attrs={"name": "date"})
    meta["date"] = date_tag["content"] if date_tag and date_tag.get("content") else ""

    # Keywords / focus keyword
    kw_tag = soup.find("meta", attrs={"name": "keywords"})
    if kw_tag and kw_tag.get("content"):
        meta["focus_keyword"] = kw_tag["content"].split(",")[0].strip()
    else:
        # Derive from first H2 or title
        meta["focus_keyword"] = _derive_focus_keyword(meta["title"])

    # Pillar and subcategory (silo structure)
    pillar_tag = soup.find("meta", attrs={"name": "pillar"})
    meta["pillar"] = pillar_tag["content"] if pillar_tag and pillar_tag.get("content") else ""
    subcat_tag = soup.find("meta", attrs={"name": "subcategory"})
    meta["subcategory"] = subcat_tag["content"] if subcat_tag and subcat_tag.get("content") else ""

    # Article type (seo / support)
    at_tag = soup.find("meta", attrs={"name": "article-type"})
    meta["article_type"] = at_tag["content"] if at_tag and at_tag.get("content") else "support"

    # Schema JSON-LD
    schema_tag = soup.find("script", attrs={"type": "application/ld+json"})
    meta["schema"] = schema_tag.string.strip() if schema_tag and schema_tag.string else ""

    # Cover image (from HTML comment or og:image)
    cover_comment = _extract_comment(html, "coverImage")
    meta["cover_image_local"] = cover_comment or meta.get("og_image", "")

    # Article body — extract <article> or <body> content
    article_tag = soup.find("article")
    if article_tag:
        meta["content_html"] = str(article_tag)
    else:
        body = soup.find("body")
        meta["content_html"] = str(body) if body else html

    # Extract all image tags with src and alt
    meta["images"] = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        width = img.get("width", "")
        height = img.get("height", "")
        meta["images"].append({
            "src": src,
            "alt": alt,
            "width": width,
            "height": height,
        })

    # Slug
    meta["slug"] = generate_slug(meta["title"])

    return meta


def _extract_comment(html: str, key: str) -> str:
    """Extract value from HTML comment like <!-- coverImage: images/cover.webp -->."""
    pattern = rf"<!--\s*{key}:\s*(.+?)\s*-->"
    match = re.search(pattern, html)
    return match.group(1).strip() if match else ""


def _derive_focus_keyword(title: str) -> str:
    """Derive a focus keyword from the article title."""
    # Remove common patterns
    title = re.sub(r"\b(a |an |the |how to |what is |why |when |where )\b", " ", title.lower())
    title = re.sub(r"\b(20\d{2})\b", "", title)  # Remove years
    title = re.sub(r"[:\-\|–—?!]", " ", title)
    words = [w for w in title.split() if w not in FILLER_WORDS and len(w) > 2]
    # Take first 3-4 meaningful words
    return " ".join(words[:4]).strip()


def clean_content(html: str, cover_src: str) -> str:
    """Clean article content before WordPress upload.

    - Removes the cover image from the body (WordPress displays it as featured image)
    - Strips [INTERNAL-LINK: ...] placeholders
    - Removes "Continue Reading" sections where all links are placeholders
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove cover image from body — match by src ending with -featured
    if cover_src:
        cover_name = Path(cover_src).name
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if Path(src).name == cover_name or src.endswith("-featured.webp"):
                # If the img is the only child of a <figure>, remove the figure
                parent = img.parent
                if parent and parent.name == "figure" and len(parent.find_all(recursive=False)) <= 2:
                    parent.decompose()
                else:
                    img.decompose()
                break

    # Remove "Continue Reading" sections where all links are [INTERNAL-LINK] placeholders
    for heading in soup.find_all(["h2", "h3"]):
        heading_text = heading.get_text(strip=True).lower()
        if "continue reading" in heading_text or "read next" in heading_text or "related articles" in heading_text:
            # Collect all sibling elements until next heading of same or higher level
            to_remove = [heading]
            level = int(heading.name[1])  # 2 for h2, 3 for h3
            sibling = heading.find_next_sibling()
            while sibling:
                if sibling.name and sibling.name in ["h1", "h2", "h3"] and int(sibling.name[1]) <= level:
                    break
                to_remove.append(sibling)
                sibling = sibling.find_next_sibling()

            # Check if the section only contains [INTERNAL-LINK] placeholders (no real links)
            section_text = " ".join(el.get_text(strip=True) for el in to_remove if hasattr(el, "get_text"))
            has_real_links = False
            for el in to_remove:
                if hasattr(el, "find_all"):
                    for a in el.find_all("a"):
                        href = a.get("href", "")
                        if href and not href.startswith("#"):
                            has_real_links = True
                            break

            # Remove if no real links (only placeholders or empty bullets)
            if not has_real_links:
                for el in to_remove:
                    el.decompose()

    content = str(soup)

    # Strip [INTERNAL-LINK: anchor text → target description] markers
    # They may appear bare or wrapped in <p> tags
    content = re.sub(r"<p>\s*\[INTERNAL-LINK:[^\]]*\]\s*</p>\s*", "", content)
    content = re.sub(r"\[INTERNAL-LINK:[^\]]*\]", "", content)

    return content


def extract_faq_items(html: str) -> list[dict]:
    """Extract FAQ question/answer pairs from article HTML."""
    soup = BeautifulSoup(html, "html.parser")
    faqs = []

    # Find FAQ heading
    faq_heading = None
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True).lower()
        if "frequently asked" in text or text == "faq":
            faq_heading = h2
            break

    if not faq_heading:
        return faqs

    # Collect elements between this h2 and the next h2
    current = faq_heading.find_next_sibling()
    while current and current.name != "h2":
        if current.name == "div" and "faq-item" in (current.get("class") or []):
            h3 = current.find("h3")
            p = current.find("p")
            if h3 and p:
                faqs.append({
                    "question": h3.get_text(strip=True),
                    "answer": p.get_text(strip=True),
                })
        elif current.name == "h3":
            question = current.get_text(strip=True)
            answer_tag = current.find_next_sibling("p")
            if answer_tag:
                faqs.append({"question": question, "answer": answer_tag.get_text(strip=True)})
        current = current.find_next_sibling()

    return faqs


def generate_schema_json_ld(
    meta: dict,
    site_url: str,
    category: str,
    cover_url: str | None = None,
) -> str:
    """Generate a @graph JSON-LD schema string from article metadata."""
    site_url = site_url.rstrip("/")
    slug = meta["slug"]
    article_url = f"{site_url}/{slug}"
    date_published = meta.get("date") or datetime.date.today().isoformat()
    author_name = meta.get("author") or AUTHOR_NAME
    author_slug = author_name.lower().replace(" ", "-")
    image_url = cover_url or meta.get("og_image", "")

    # Word count from content
    content_text = BeautifulSoup(meta.get("content_html", ""), "html.parser").get_text()
    word_count = len(content_text.split())

    graph = []

    # Organization
    graph.append({
        "@type": "Organization",
        "@id": f"{site_url}#organization",
        "name": SITE_NAME,
        "url": site_url,
        "logo": {
            "@type": "ImageObject",
            "url": f"{site_url}{SITE_LOGO_PATH}",
            "width": SITE_LOGO_WIDTH,
            "height": SITE_LOGO_HEIGHT,
        },
    })

    # Person (author)
    graph.append({
        "@type": "Person",
        "@id": f"{site_url}/author/{author_slug}#person",
        "name": author_name,
        "url": f"{site_url}/author/{author_slug}",
        "worksFor": {"@id": f"{site_url}#organization"},
    })

    # ImageObject (cover)
    if image_url:
        graph.append({
            "@type": "ImageObject",
            "@id": f"{article_url}#primaryimage",
            "url": image_url,
            "width": 1200,
            "height": 630,
            "caption": meta.get("og_title") or meta.get("title", ""),
        })

    # BlogPosting
    blog_posting = {
        "@type": "BlogPosting",
        "@id": f"{article_url}#article",
        "headline": meta.get("title", "")[:110],
        "description": meta.get("description", "")[:160],
        "datePublished": date_published,
        "dateModified": date_published,
        "author": {"@id": f"{site_url}/author/{author_slug}#person"},
        "publisher": {"@id": f"{site_url}#organization"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": article_url},
        "wordCount": word_count,
        "inLanguage": "en",
        "articleSection": category,
    }
    if image_url:
        blog_posting["image"] = {"@id": f"{article_url}#primaryimage"}
    if meta.get("focus_keyword"):
        blog_posting["keywords"] = meta["focus_keyword"]
    graph.append(blog_posting)

    # BreadcrumbList
    category_slug = category.lower().replace(" & ", "-").replace(" ", "-")
    graph.append({
        "@type": "BreadcrumbList",
        "@id": f"{article_url}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site_url},
            {"@type": "ListItem", "position": 2, "name": category,
             "item": f"{site_url}/category/{category_slug}"},
            {"@type": "ListItem", "position": 3, "name": meta.get("title", ""),
             "item": article_url},
        ],
    })

    # FAQPage (conditional)
    faq_items = extract_faq_items(meta.get("content_html", ""))
    if faq_items:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{article_url}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
                }
                for faq in faq_items
            ],
        })

    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)


def generate_slug(title: str) -> str:
    """Generate a short, clean URL slug from title (2-4 keywords)."""
    # Lowercase, remove punctuation
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s]", " ", slug)
    slug = re.sub(r"\b(20\d{2})\b", "", slug)  # Remove years
    words = slug.split()
    # Filter filler words, keep meaningful ones
    meaningful = [w for w in words if w not in FILLER_WORDS and len(w) > 2]
    # Take 2-4 keywords
    slug_words = meaningful[:4]
    return "-".join(slug_words)


# ---------------------------------------------------------------------------
# WordPress API Operations
# ---------------------------------------------------------------------------

class WordPressClient:
    """WordPress REST API client for uploading posts and media."""

    def __init__(self, url: str, username: str, app_password: str, dry_run: bool = False):
        self.base_url = url
        self.api_url = f"{url}/wp-json/wp/v2"
        self.auth = make_auth_header(username, app_password)
        self.dry_run = dry_run
        self.session = requests.Session()
        # Only disable SSL verification for the known staging domain (self-signed cert)
        if "cloudwaysapps.com" in url:
            self.session.verify = False
        self.session.headers.update(self.auth)

    def test_connection(self) -> bool:
        """Verify credentials work."""
        try:
            resp = self.session.get(f"{self.api_url}/users/me", timeout=15)
            if resp.status_code == 200:
                user = resp.json()
                print(f"  Authenticated as: {user.get('name', 'unknown')} ({user.get('slug', '')})")
                return True
            else:
                print(f"  Auth failed: {resp.status_code} — {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            print(f"  Connection error: {e}")
            return False

    def upload_image(self, image_path: Path, alt_text: str = "", description: str = "") -> dict | None:
        """Upload an image to WordPress Media Library. Returns media object or None."""
        if self.dry_run:
            print(f"  [DRY RUN] Would upload: {image_path.name}")
            return {"id": 0, "source_url": f"https://example.com/wp-content/uploads/{image_path.name}"}

        content_type = CONTENT_TYPE_MAP.get(image_path.suffix.lower(), "application/octet-stream")
        filename = image_path.name

        headers = {
            **self.auth,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
        }

        try:
            with open(image_path, "rb") as f:
                resp = self.session.post(
                    f"{self.api_url}/media",
                    headers=headers,
                    data=f.read(),
                    timeout=60,
                )

            if resp.status_code not in (200, 201):
                print(f"  Image upload failed ({resp.status_code}): {resp.text[:200]}")
                return None

            media = resp.json()
            media_id = media["id"]

            # Set alt text and description via update
            if alt_text or description:
                update_data = {}
                if alt_text:
                    update_data["alt_text"] = alt_text
                if description:
                    update_data["description"] = description
                self.session.post(
                    f"{self.api_url}/media/{media_id}",
                    json=update_data,
                    timeout=15,
                )

            return media

        except requests.RequestException as e:
            print(f"  Image upload error: {e}")
            return None

    def find_category(self, name: str, parent_id: int | None = None) -> int | None:
        """Find an existing category by name (under optional parent).

        WordPress returns category names with HTML entities (e.g. ``&amp;``),
        so we decode before comparing.  Never creates categories — if the
        category doesn't exist, something is wrong with the mapping.
        """
        if self.dry_run:
            print(f"  [DRY RUN] Would look up category: {name}")
            return 1

        try:
            resp = self.session.get(
                f"{self.api_url}/categories",
                params={"search": name, "per_page": 50},
                timeout=15,
            )
            if resp.status_code == 200:
                cats = resp.json()
                for cat in cats:
                    decoded = _html_decode(cat["name"])
                    matches_name = decoded.lower() == name.lower()
                    matches_parent = parent_id is None or cat["parent"] == parent_id
                    if matches_name and matches_parent:
                        return cat["id"]

            print(f"  Warning: Category not found on site: '{name}'"
                  f"{f' (parent ID {parent_id})' if parent_id else ''}")

        except requests.RequestException as e:
            print(f"  Category error: {e}")

        return None

    def create_draft(self, data: dict) -> dict | None:
        """Create a draft post. Returns post object or None."""
        if self.dry_run:
            print(f"  [DRY RUN] Would create draft: {data.get('title', 'untitled')}")
            print(f"  [DRY RUN] Slug: {data.get('slug', '')}")
            print(f"  [DRY RUN] Categories: {data.get('categories', [])}")
            print(f"  [DRY RUN] Featured media: {data.get('featured_media', 'none')}")
            meta = data.get("meta", {})
            if meta:
                print(f"  [DRY RUN] RankMath fields:")
                for k, v in meta.items():
                    val = str(v)[:80] + "..." if len(str(v)) > 80 else str(v)
                    print(f"    {k}: {val}")
            return {"id": 0, "link": "https://example.com/?p=0"}

        try:
            resp = self.session.post(
                f"{self.api_url}/posts",
                json=data,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                print(f"  Post creation failed ({resp.status_code}): {resp.text[:500]}")
                return None
        except requests.RequestException as e:
            print(f"  Post creation error: {e}")
            return None


# ---------------------------------------------------------------------------
# Upload Pipeline
# ---------------------------------------------------------------------------

def _html_decode(s: str) -> str:
    """Decode HTML entities (WordPress returns &amp; in category names)."""
    return html_module.unescape(s)


# ---------------------------------------------------------------------------
# Category mapping — must match the actual WordPress taxonomy.
# Pillar keywords are checked first; subcategory keywords narrow within a
# pillar.  Keys are lowercase substrings matched against the article title.
# ---------------------------------------------------------------------------

# Pillar names exactly as they appear in WordPress (HTML-decoded)
_PILLAR_KEYWORDS: list[tuple[str, str]] = [
    # Check specific/longer phrases before generic ones
    ("floating solar",       "Solar Energy"),
    ("solar panel",          "Solar Energy"),
    ("solar farm",           "Solar Energy"),
    ("solar cost",           "Solar Energy"),
    ("solar install",        "Solar Energy"),
    ("solar energy",         "Solar Energy"),
    ("solar",                "Solar Energy"),
    ("photovoltaic",         "Solar Energy"),
    ("pv system",            "Solar Energy"),
    ("offshore wind",        "Wind Power"),
    ("wind farm",            "Wind Power"),
    ("wind turbin",          "Wind Power"),
    ("wind power",           "Wind Power"),
    ("wind energy",          "Wind Power"),
    ("wind",                 "Wind Power"),
    ("hydroelectric",        "Hydroelectric Power"),
    ("hydropower",           "Hydroelectric Power"),
    ("hydro dam",            "Hydroelectric Power"),
    ("pumped storage",       "Hydroelectric Power"),
    ("micro hydro",          "Hydroelectric Power"),
    ("biomass",              "Bioenergy"),
    ("biogas",               "Bioenergy"),
    ("biofuel",              "Bioenergy"),
    ("waste-to-energy",      "Bioenergy"),
    ("waste to energy",      "Bioenergy"),
    ("bioenergy",            "Bioenergy"),
    ("battery storage",      "Energy Storage & Grid Infrastructure"),
    ("energy storage",       "Energy Storage & Grid Infrastructure"),
    ("grid infra",           "Energy Storage & Grid Infrastructure"),
    ("smart grid",           "Energy Storage & Grid Infrastructure"),
    ("battery",              "Energy Storage & Grid Infrastructure"),
    ("ev charg",             "Electric Vehicles & Clean Transport"),
    ("electric vehicle",     "Electric Vehicles & Clean Transport"),
    ("electric car",         "Electric Vehicles & Clean Transport"),
    ("ev industry",          "Electric Vehicles & Clean Transport"),
    (" ev ",                 "Electric Vehicles & Clean Transport"),
    ("green building",       "Green Buildings & Energy Efficiency"),
    ("energy efficien",      "Green Buildings & Energy Efficiency"),
    ("district cooling",     "Green Buildings & Energy Efficiency"),
    ("building certification", "Green Buildings & Energy Efficiency"),
    ("leed",                 "Green Buildings & Energy Efficiency"),
    ("subsid",               "Policy, Economics & Thailand Context"),
    ("incentive",            "Policy, Economics & Thailand Context"),
    ("electricity pric",     "Policy, Economics & Thailand Context"),
    ("tariff",               "Policy, Economics & Thailand Context"),
    ("energy policy",        "Policy, Economics & Thailand Context"),
    ("national energy",      "Policy, Economics & Thailand Context"),
    ("feed-in",              "Policy, Economics & Thailand Context"),
    ("pdp",                  "Policy, Economics & Thailand Context"),
    ("community energy",     "Policy, Economics & Thailand Context"),
]

# Subcategory keywords mapped to their exact WordPress subcategory names.
# Each entry: (keyword, subcategory_name, parent_pillar)
_SUBCATEGORY_KEYWORDS: list[tuple[str, str, str]] = [
    # Solar Energy
    ("solar cost",           "Solar Costs & Financing",                          "Solar Energy"),
    ("solar financ",         "Solar Costs & Financing",                          "Solar Energy"),
    ("solar loan",           "Solar Costs & Financing",                          "Solar Energy"),
    ("solar roi",            "Solar Costs & Financing",                          "Solar Energy"),
    ("payback",              "Solar Costs & Financing",                          "Solar Energy"),
    ("solar install",        "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("solar permit",         "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("net meter",            "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("grid connect",         "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("mea",                  "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("pea",                  "Installation, Permits & Grid Connection",          "Solar Energy"),
    ("solar maintenance",    "Climate, Performance & Maintenance",               "Solar Energy"),
    ("solar performance",    "Climate, Performance & Maintenance",               "Solar Energy"),
    ("panel degradat",       "Climate, Performance & Maintenance",               "Solar Energy"),
    ("tropical climate",     "Climate, Performance & Maintenance",               "Solar Energy"),
    ("solar farm",           "Utility-Scale Solar & Innovation",                 "Solar Energy"),
    ("floating solar",       "Utility-Scale Solar & Innovation",                 "Solar Energy"),
    ("utility-scale",        "Utility-Scale Solar & Innovation",                 "Solar Energy"),
    ("bifacial",             "Utility-Scale Solar & Innovation",                 "Solar Energy"),
    # Wind Power
    ("onshore wind",         "Onshore Wind Farms",                               "Wind Power"),
    ("wind farm",            "Onshore Wind Farms",                               "Wind Power"),
    ("offshore wind",        "Offshore Wind & Future Development",               "Wind Power"),
    ("wind limit",           "When Wind Works (and When It Doesn't)",            "Wind Power"),
    ("wind intermit",        "When Wind Works (and When It Doesn't)",            "Wind Power"),
    ("wind resource",        "When Wind Works (and When It Doesn't)",            "Wind Power"),
    # Hydroelectric Power
    ("large dam",            "Large Dams & Major Projects",                      "Hydroelectric Power"),
    ("mega dam",             "Large Dams & Major Projects",                      "Hydroelectric Power"),
    ("micro hydro",          "Small-Scale & Micro Hydro",                        "Hydroelectric Power"),
    ("small hydro",          "Small-Scale & Micro Hydro",                        "Hydroelectric Power"),
    ("run-of-river",         "Small-Scale & Micro Hydro",                        "Hydroelectric Power"),
    ("hydro environment",    "Environmental & Social Impacts",                   "Hydroelectric Power"),
    ("dam impact",           "Environmental & Social Impacts",                   "Hydroelectric Power"),
    ("pumped storage",       "Pumped Storage & Energy Storage",                  "Hydroelectric Power"),
    ("pumped hydro",         "Pumped Storage & Energy Storage",                  "Hydroelectric Power"),
    # Bioenergy
    ("biomass",              "Agricultural Biomass",                              "Bioenergy"),
    ("rice husk",            "Agricultural Biomass",                              "Bioenergy"),
    ("bagasse",              "Agricultural Biomass",                              "Bioenergy"),
    ("crop residue",         "Agricultural Biomass",                              "Bioenergy"),
    ("biogas",               "Biogas Systems",                                   "Bioenergy"),
    ("anaerobic digest",     "Biogas Systems",                                   "Bioenergy"),
    ("biofuel",              "Biofuels",                                         "Bioenergy"),
    ("biodiesel",            "Biofuels",                                         "Bioenergy"),
    ("ethanol",              "Biofuels",                                         "Bioenergy"),
    ("waste-to-energy",      "Waste-to-Energy",                                  "Bioenergy"),
    ("waste to energy",      "Waste-to-Energy",                                  "Bioenergy"),
    ("incinerat",            "Waste-to-Energy",                                  "Bioenergy"),
    # Energy Storage & Grid Infrastructure
    ("battery storage",      "Battery Storage Systems",                          "Energy Storage & Grid Infrastructure"),
    ("lithium",              "Battery Storage Systems",                          "Energy Storage & Grid Infrastructure"),
    ("bess",                 "Battery Storage Systems",                          "Energy Storage & Grid Infrastructure"),
    ("grid infra",           "Grid Infrastructure & Challenges",                 "Energy Storage & Grid Infrastructure"),
    ("smart grid",           "Grid Infrastructure & Challenges",                 "Energy Storage & Grid Infrastructure"),
    ("transmiss",            "Grid Infrastructure & Challenges",                 "Energy Storage & Grid Infrastructure"),
    ("grid stabil",          "Grid Infrastructure & Challenges",                 "Energy Storage & Grid Infrastructure"),
    ("flow battery",         "Alternative Storage Technologies",                 "Energy Storage & Grid Infrastructure"),
    ("hydrogen storage",     "Alternative Storage Technologies",                 "Energy Storage & Grid Infrastructure"),
    ("compressed air",       "Alternative Storage Technologies",                 "Energy Storage & Grid Infrastructure"),
    ("thermal storage",      "Alternative Storage Technologies",                 "Energy Storage & Grid Infrastructure"),
    # Electric Vehicles & Clean Transport
    ("buying ev",            "Buying & Owning an EV",                            "Electric Vehicles & Clean Transport"),
    ("owning ev",            "Buying & Owning an EV",                            "Electric Vehicles & Clean Transport"),
    ("ev cost",              "Buying & Owning an EV",                            "Electric Vehicles & Clean Transport"),
    ("ev price",             "Buying & Owning an EV",                            "Electric Vehicles & Clean Transport"),
    ("ev review",            "Buying & Owning an EV",                            "Electric Vehicles & Clean Transport"),
    ("ev charg",             "EV Charging Infrastructure",                       "Electric Vehicles & Clean Transport"),
    ("charging station",     "EV Charging Infrastructure",                       "Electric Vehicles & Clean Transport"),
    ("ev industry",          "Thailand's EV Industry",                           "Electric Vehicles & Clean Transport"),
    ("ev manufactur",        "Thailand's EV Industry",                           "Electric Vehicles & Clean Transport"),
    ("ev market",            "Thailand's EV Industry",                           "Electric Vehicles & Clean Transport"),
    ("ev policy",            "Thailand's EV Industry",                           "Electric Vehicles & Clean Transport"),
    # Green Buildings & Energy Efficiency
    ("district cooling",     "District Cooling Systems",                         "Green Buildings & Energy Efficiency"),
    ("energy efficien",      "Practical Energy Efficiency",                      "Green Buildings & Energy Efficiency"),
    ("insulation",           "Practical Energy Efficiency",                      "Green Buildings & Energy Efficiency"),
    ("energy saving",        "Practical Energy Efficiency",                      "Green Buildings & Energy Efficiency"),
    ("cooling system",       "Practical Energy Efficiency",                      "Green Buildings & Energy Efficiency"),
    ("leed",                 "Certification & Standards",                        "Green Buildings & Energy Efficiency"),
    ("green certif",         "Certification & Standards",                        "Green Buildings & Energy Efficiency"),
    ("trees",                "Certification & Standards",                        "Green Buildings & Energy Efficiency"),
    ("building standard",    "Certification & Standards",                        "Green Buildings & Energy Efficiency"),
    # Policy, Economics & Thailand Context
    ("subsid",               "Incentives, Subsidies & Tax Breaks",               "Policy, Economics & Thailand Context"),
    ("incentive",            "Incentives, Subsidies & Tax Breaks",               "Policy, Economics & Thailand Context"),
    ("tax break",            "Incentives, Subsidies & Tax Breaks",               "Policy, Economics & Thailand Context"),
    ("boi",                  "Incentives, Subsidies & Tax Breaks",               "Policy, Economics & Thailand Context"),
    ("electricity pric",     "Electricity Pricing & Economics",                  "Policy, Economics & Thailand Context"),
    ("ft rate",              "Electricity Pricing & Economics",                   "Policy, Economics & Thailand Context"),
    ("tariff",               "Electricity Pricing & Economics",                  "Policy, Economics & Thailand Context"),
    ("feed-in",              "Electricity Pricing & Economics",                  "Policy, Economics & Thailand Context"),
    ("energy price",         "Electricity Pricing & Economics",                  "Policy, Economics & Thailand Context"),
    ("pdp",                  "National Energy Goals & Plans",                    "Policy, Economics & Thailand Context"),
    ("national energy",      "National Energy Goals & Plans",                    "Policy, Economics & Thailand Context"),
    ("aedp",                 "National Energy Goals & Plans",                    "Policy, Economics & Thailand Context"),
    ("carbon neutral",       "National Energy Goals & Plans",                    "Policy, Economics & Thailand Context"),
    ("net zero",             "National Energy Goals & Plans",                    "Policy, Economics & Thailand Context"),
    ("regional energy",      "Regional Energy Landscapes",                      "Policy, Economics & Thailand Context"),
    ("isaan",                "Regional Energy Landscapes",                      "Policy, Economics & Thailand Context"),
    ("southern thailand",    "Regional Energy Landscapes",                      "Policy, Economics & Thailand Context"),
    ("community energy",     "Community & Cooperative Energy",                   "Policy, Economics & Thailand Context"),
    ("cooperat",             "Community & Cooperative Energy",                   "Policy, Economics & Thailand Context"),
    ("prosumer",             "Community & Cooperative Energy",                   "Policy, Economics & Thailand Context"),
]


# WordPress category IDs for the silo hierarchy.
# These match the categories already created in WordPress.
# Keep in sync with claude-blog/scripts/wordpress_upload.py.
SILO_CATEGORY_IDS: dict[str, dict[str, int]] = {
    "Solar Energy": {
        "_pillar": 68,
        "Solar Costs & Financing": 69,
        "Installation, Permits & Grid Connection": 70,
        "Climate, Performance & Maintenance": 71,
        "Utility-Scale Solar & Innovation": 72,
    },
    "Wind Power": {
        "_pillar": 73,
        "Onshore Wind Farms": 74,
        "Offshore Wind & Future Development": 75,
        "When Wind Works (and When It Doesn't)": 76,
    },
    "Hydroelectric Power": {
        "_pillar": 77,
        "Large Dams & Major Projects": 78,
        "Small-Scale & Micro Hydro": 79,
        "Environmental & Social Impacts": 80,
        "Pumped Storage & Energy Storage": 81,
    },
    "Bioenergy": {
        "_pillar": 82,
        "Agricultural Biomass": 83,
        "Biogas Systems": 84,
        "Biofuels": 85,
        "Waste-to-Energy": 86,
    },
    "Energy Storage & Grid Infrastructure": {
        "_pillar": 87,
        "Battery Storage Systems": 88,
        "Grid Infrastructure & Challenges": 89,
        "Alternative Storage Technologies": 90,
    },
    "Electric Vehicles & Clean Transport": {
        "_pillar": 91,
        "Buying & Owning an EV": 92,
        "EV Charging Infrastructure": 93,
        "Thailand's EV Industry": 94,
    },
    "Green Buildings & Energy Efficiency": {
        "_pillar": 95,
        "Practical Energy Efficiency": 96,
        "District Cooling Systems": 97,
        "Certification & Standards": 98,
    },
    "Policy, Economics & Thailand Context": {
        "_pillar": 99,
        "Incentives, Subsidies & Tax Breaks": 100,
        "Electricity Pricing & Economics": 101,
        "National Energy Goals & Plans": 102,
        "Regional Energy Landscapes": 103,
        "Community & Cooperative Energy": 104,
    },
}


def resolve_silo_categories(pillar: str, subcategory: str) -> list[int]:
    """Resolve pillar and subcategory names to WordPress category IDs.

    Returns a list of category IDs (pillar + subcategory if found).
    Names must match SILO_CATEGORY_IDS keys exactly.
    """
    pillar_data = SILO_CATEGORY_IDS.get(pillar)
    if not pillar_data:
        return []

    cat_ids = [pillar_data["_pillar"]]

    if subcategory and subcategory in pillar_data:
        cat_ids.append(pillar_data[subcategory])
    elif subcategory:
        print(f"  Warning: Subcategory '{subcategory}' not found under pillar '{pillar}' — only pillar assigned")

    return cat_ids


def derive_category(title: str) -> tuple[str, str | None]:
    """Derive WordPress pillar and subcategory from the article title.

    Returns (pillar_name, subcategory_name | None).  Names match the actual
    WordPress taxonomy exactly (HTML-decoded).
    """
    title_lower = f" {title.lower()} "  # pad so " ev " matches

    # 1. Find pillar
    pillar = None
    for keyword, pillar_name in _PILLAR_KEYWORDS:
        if keyword in title_lower:
            pillar = pillar_name
            break

    if pillar is None:
        pillar = "Policy, Economics & Thailand Context"  # safest fallback

    # 2. Find subcategory within that pillar
    subcategory = None
    for keyword, subcat_name, parent_pillar in _SUBCATEGORY_KEYWORDS:
        if parent_pillar == pillar and keyword in title_lower:
            subcategory = subcat_name
            break

    return pillar, subcategory


def upload_article(html_path: Path, images_dir: Path | None, dry_run: bool = False, category: str | None = None):
    """Main upload pipeline: parse → upload images → replace paths → create draft."""

    print(f"\n{'=' * 60}")
    print(f"WordPress Draft Upload")
    print(f"{'=' * 60}")

    # 1. Load WordPress config
    print("\n[1/7] Loading WordPress credentials...")
    if dry_run:
        # In dry-run mode, use placeholder credentials if not set
        env_path = Path(__file__).resolve().parent.parent / ".env"
        env = load_env(env_path)
        wp_url = os.environ.get("WORDPRESS_URL") or env.get("WORDPRESS_URL", "https://example.com")
        wp_user = os.environ.get("WORDPRESS_USERNAME") or env.get("WORDPRESS_USERNAME", "dry-run")
        wp_pass = os.environ.get("WORDPRESS_APP_PASSWORD") or env.get("WORDPRESS_APP_PASSWORD", "dry-run")
    else:
        wp_url, wp_user, wp_pass = get_wp_config()
    print(f"  Site: {wp_url}")

    client = WordPressClient(wp_url, wp_user, wp_pass, dry_run=dry_run)

    # 2. Test connection
    print("\n[2/7] Testing connection...")
    if not dry_run and not client.test_connection():
        print("\nFailed to authenticate. Check your credentials.")
        sys.exit(1)
    elif dry_run:
        print("  [DRY RUN] Skipping connection test")

    # 3. Parse article
    print(f"\n[3/7] Parsing article: {html_path.name}")
    meta = parse_article(html_path)
    print(f"  Title: {meta['title']}")
    print(f"  Slug: {meta['slug']}")
    print(f"  Description: {meta['description'][:80]}...")
    print(f"  Focus keyword: {meta['focus_keyword']}")
    print(f"  Images found in HTML: {len(meta['images'])}")

    # Resolve images directory
    if images_dir is None:
        # Default: look for images/ relative to the HTML file
        images_dir = html_path.parent / "images"
    if not images_dir.exists():
        print(f"  Warning: Images directory not found: {images_dir}")
        images_dir = None

    # 4. Upload images
    print(f"\n[4/7] Uploading images to Media Library...")
    media_map = {}  # local_path -> {id, url}
    cover_media_id = None
    cover_media_url = None

    if images_dir:
        # Build alt text lookup from parsed images and collect referenced filenames
        alt_lookup = {}
        referenced_filenames = set()
        for img_info in meta["images"]:
            src = img_info["src"]
            basename = Path(src).name
            alt_lookup[basename] = img_info["alt"]
            referenced_filenames.add(basename)

        # Only upload images that are actually referenced in the HTML
        image_files = sorted(images_dir.glob("*"))
        image_files = [f for f in image_files if f.suffix.lower() in CONTENT_TYPE_MAP and f.name in referenced_filenames]

        if len(list(images_dir.glob("*"))) != len(image_files):
            total = len([f for f in images_dir.glob("*") if f.suffix.lower() in CONTENT_TYPE_MAP])
            print(f"  Filtered: {len(image_files)} referenced in HTML (skipped {total - len(image_files)} stale)")

        for img_file in image_files:
            alt = alt_lookup.get(img_file.name, img_file.stem.replace("-", " ").title())
            print(f"  Uploading: {img_file.name} (alt: {alt[:50]}...)")

            media = client.upload_image(img_file, alt_text=alt, description=alt)
            if media:
                source_url = media.get("source_url", "")
                media_map[img_file.name] = {
                    "id": media["id"],
                    "url": source_url,
                }
                print(f"    -> ID: {media['id']}, URL: {source_url[:80]}")

                # Detect cover image (ends in -featured)
                stem = img_file.stem.lower()
                if stem.endswith("-featured"):
                    cover_media_id = media["id"]
                    cover_media_url = source_url
                    print(f"    -> Set as featured image")

            # Rate limit: 1 second between uploads
            if not dry_run:
                time.sleep(1)

    if not cover_media_id and media_map:
        # Fallback: use first uploaded image as cover
        first = next(iter(media_map.values()))
        cover_media_id = first["id"]
        cover_media_url = first["url"]
        print(f"  Fallback cover: ID {cover_media_id}")

    print(f"  Uploaded: {len(media_map)} images")

    # 5. Clean content and replace image paths
    print(f"\n[5/7] Cleaning content and replacing image paths...")
    content = clean_content(meta["content_html"], meta["cover_image_local"])
    print(f"  Removed cover image from body (displayed as featured image)")
    print(f"  Stripped placeholder-only Continue Reading / Read Next sections")
    print(f"  Stripped [INTERNAL-LINK] placeholders")

    for local_name, wp_media in media_map.items():
        # Replace various path patterns (break after first match to avoid
        # double-replacing — the bare filename would match inside the WP URL)
        for prefix in ["images/", "./images/", "../images/", ""]:
            old_path = f"{prefix}{local_name}"
            if old_path in content:
                content = content.replace(old_path, wp_media["url"])
                print(f"  {old_path} -> ...{wp_media['url'][-40:]}")
                break

    # 6. Resolve categories (pillar + subcategory)
    print(f"\n[6/8] Resolving categories...")
    silo_cat_ids = []

    # Prefer HTML meta tags (set by pipeline when article is generated)
    if meta.get("pillar"):
        pillar_name = meta["pillar"]
        subcategory_name = meta.get("subcategory", "")
        silo_cat_ids = resolve_silo_categories(pillar_name, subcategory_name)
        if not silo_cat_ids:
            print(f"  Warning: Pillar '{pillar_name}' not in silo map, falling back to title-based")

    # Fall back to --category flag or title-based derivation
    if not silo_cat_ids:
        if category:
            pillar_name = category
            _, subcategory_name = derive_category(meta["title"])
        else:
            pillar_name, subcategory_name = derive_category(meta["title"])
        silo_cat_ids = resolve_silo_categories(pillar_name, subcategory_name or "")

    print(f"  Pillar:      {pillar_name}")
    print(f"  Subcategory: {subcategory_name or '(none detected)'}")

    # 6b. Generate schema JSON-LD and embed in content
    print(f"\n[6b/8] Generating schema JSON-LD...")
    had_schema = bool(meta.get("schema"))
    if had_schema:
        print("  Schema already present in HTML — embedding existing")
        schema_json = meta["schema"]
    else:
        schema_json = generate_schema_json_ld(
            meta=meta,
            site_url=wp_url,
            category=pillar_name,
            cover_url=cover_media_url,
        )
        meta["schema"] = schema_json
        schema_data = json.loads(schema_json)
        type_names = [e.get("@type", "?") for e in schema_data.get("@graph", [])]
        print(f"  Generated {len(type_names)} types: {', '.join(type_names)}")

    # Embed schema as <script> tag at end of post content
    schema_tag = f'<script type="application/ld+json">\n{schema_json}\n</script>'
    content = content + "\n" + schema_tag
    print("  Embedded in post HTML (search engines read directly from page)")

    # 6c. Wrap SVG figures in Gutenberg Custom HTML block markers
    # This prevents the Gutenberg block editor from stripping inline SVGs
    # when the post is edited through wp-admin.
    def _wrap_svg_figures(html: str) -> str:
        parts = []
        pos = 0
        for m in re.finditer(r"<figure>\s*<svg", html):
            fig_start = m.start()
            fig_end = html.find("</figure>", fig_start)
            if fig_end < 0:
                continue
            fig_end += len("</figure>")
            parts.append(html[pos:fig_start])
            parts.append(f"<!-- wp:html -->\n{html[fig_start:fig_end]}\n<!-- /wp:html -->")
            pos = fig_end
        parts.append(html[pos:])
        return "".join(parts)

    svg_count = len(re.findall(r"<figure>\s*<svg", content))
    if svg_count:
        content = _wrap_svg_figures(content)
        print(f"  Wrapped {svg_count} SVG chart(s) in Gutenberg Custom HTML blocks")

    # 7. Create draft post
    print(f"\n[7/8] Creating WordPress draft...")

    if silo_cat_ids:
        category_ids = silo_cat_ids
        print(f"  Silo: {pillar_name} > {subcategory_name or '(pillar only)'} (IDs: {category_ids})")
    else:
        # Last resort: look up by name via API
        pillar_id = client.find_category(pillar_name)
        category_ids = [pillar_id] if pillar_id else []
        print(f"  Category: {pillar_name} (ID: {pillar_id}) [fallback — no silo match]")

    post_data = {
        "title": meta["title"],
        "slug": meta["slug"],
        "status": "draft",
        "content": content,
        "excerpt": meta["description"],
        "categories": category_ids,
    }

    # Featured image
    if cover_media_id is not None:
        post_data["featured_media"] = cover_media_id

    # Don't include RankMath meta in post_data — RankMath blocks custom field
    # writes via the standard WP REST API meta parameter. SEO fields are set
    # separately via the RankMath REST API after the post is created.
    post = client.create_draft(post_data)

    # Write RankMath SEO meta via its own REST API
    if post:
        post_id_for_rm = post.get("id")
        if post_id_for_rm:
            rm_meta = {
                "rank_math_title": meta["title"],
                "rank_math_description": meta["description"][:160],
                "rank_math_focus_keyword": meta["focus_keyword"],
                "rank_math_facebook_title": meta.get("og_title") or meta["title"],
                "rank_math_facebook_description": meta.get("og_description") or meta["description"],
                "rank_math_twitter_use_facebook": "on",
                "rank_math_twitter_card_type": "summary_large_image",
            }
            if cover_media_url:
                rm_meta["rank_math_facebook_image"] = cover_media_url
                if cover_media_id:
                    rm_meta["rank_math_facebook_image_id"] = str(cover_media_id)
            rankmath_resp = client.session.post(
                f"{wp_url}/wp-json/rankmath/v1/updateMeta",
                json={
                    "objectType": "post",
                    "objectID": post_id_for_rm,
                    "meta": rm_meta,
                },
                timeout=15,
            )
            if rankmath_resp.status_code == 200:
                print("  RankMath meta updated via RankMath API")
            else:
                print(f"  Warning: RankMath meta update failed ({rankmath_resp.status_code})")

    # Report
    print(f"\n{'=' * 60}")
    if post:
        post_id = post.get("id", "?")
        post_link = post.get("link", "?")
        edit_url = f"{wp_url}/wp-admin/post.php?post={post_id}&action=edit" if post_id != "?" else "?"

        print(f"Draft created successfully!")
        print(f"  Post ID:   {post_id}")
        print(f"  Edit URL:  {edit_url}")
        print(f"  Permalink: {post_link}")
        print(f"  Slug:      {meta['slug']}")
        print(f"\n  SEO Fields Set:")
        print(f"    Title:          {meta['title'][:60]}...")
        print(f"    Description:    {meta['description'][:60]}...")
        print(f"    Focus keyword:  {meta['focus_keyword']}")
        print(f"    OG image:       {'set' if cover_media_url else 'not set'}")
        print(f"    Featured image: {'set' if cover_media_id is not None else 'not set'}")
        schema_status = "embedded (from source)" if had_schema else "embedded (auto-generated)"
        print(f"    Schema:         {schema_status}")
        cat_display = f"{pillar_name} → {subcategory_name}" if subcategory_name else pillar_name
        print(f"    Category:       {cat_display}")
        print(f"    Images:         {len(media_map)} uploaded")
    else:
        print("Failed to create draft. Check errors above.")
    print(f"{'=' * 60}\n")

    # Send Discord notification for new drafts
    if post and post.get("id") and post.get("id") != 0:
        _env_path = Path(__file__).resolve().parent.parent / ".env"
        _env = load_env(_env_path)
        discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL") or _env.get("DISCORD_WEBHOOK_URL")
        if discord_webhook:
            try:
                cat_display = f"{pillar_name} → {subcategory_name}" if subcategory_name else pillar_name
                preview_url = f"{wp_url}/?p={post.get('id')}&preview=true"
                discord_payload = {
                    "embeds": [{
                        "title": f"📝 Draft Ready: {meta['title'][:200]}",
                        "url": preview_url,
                        "color": 0x22c55e,
                        "fields": [
                            {"name": "Post ID", "value": str(post.get("id")), "inline": True},
                            {"name": "Category", "value": cat_display, "inline": True},
                            {"name": "Images", "value": str(len(media_map)), "inline": True},
                            {"name": "Focus Keyword", "value": meta.get("focus_keyword", "—"), "inline": False},
                            {"name": "Edit", "value": f"[Open editor]({edit_url})", "inline": False},
                        ],
                        "footer": {"text": "Green Energy Thailand • Video Pipeline"},
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }]
                }
                disc_resp = requests.post(discord_webhook, json=discord_payload, timeout=10)
                if disc_resp.status_code in (200, 204):
                    print("  Discord notification sent ✓")
                else:
                    print(f"  Discord notification failed ({disc_resp.status_code})")
            except Exception as e:
                print(f"  Discord notification skipped: {e}")

    return post


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload a generated blog article to WordPress as a draft.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/wordpress_upload.py output/article.html
    python scripts/wordpress_upload.py output/article.html --images output/images
    python scripts/wordpress_upload.py output/article.html --dry-run

Environment (.env):
    WORDPRESS_URL=https://wordpress-1171553-6117772.cloudwaysapps.com
    WORDPRESS_USERNAME=admin
    WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx
        """,
    )
    parser.add_argument("html_file", type=Path, help="Path to the generated HTML article")
    parser.add_argument("--images", type=Path, default=None, help="Path to images directory (default: <html_dir>/images)")
    parser.add_argument("--category", type=str, default=None, help="WordPress category name (pillar from categories.json). If omitted, derived from title keywords.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and show what would be uploaded without making API calls")

    args = parser.parse_args()

    if not args.html_file.exists():
        print(f"Error: File not found: {args.html_file}")
        sys.exit(1)

    upload_article(args.html_file, args.images, dry_run=args.dry_run, category=args.category)


if __name__ == "__main__":
    main()
