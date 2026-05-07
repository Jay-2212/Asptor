"""Core publishing logic for generating the static site."""
import json
import os
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, List, Optional

from scripts.clean.schema import Article
from .templates import INDEX_TEMPLATE, ARTICLE_ITEM_TEMPLATE, ARTICLE_PAGE_TEMPLATE, BASE_HEAD, SECTION_TEMPLATE

# ------------------------------------------------------------------
# Publisher
# ------------------------------------------------------------------

class Publisher:
    def __init__(self, processed_root: Path, site_root: Path):
        self.processed_root = processed_root
        self.site_root = site_root
        self.content_dir = site_root / "content"

    def ensure_dirs(self):
        """Ensure the site and content directories exist."""
        self.site_root.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def load_all_articles(self) -> List[Article]:
        """Load all articles from all sources in processed_root and deduplicate by hash."""
        articles_by_hash: Dict[str, Article] = {}

        if not self.processed_root.exists():
            return []

        # Walk through source directories
        for source_dir in self.processed_root.iterdir():
            if not source_dir.is_dir():
                continue

            # Load all JSON files in the source directory
            for json_file in source_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                # Safe loading to handle schema updates
                                article = Article.from_dict(item)
                                # Keep the latest one based on fetched_at if hash is same
                                if article.hash not in articles_by_hash or \
                                   article.fetched_at > articles_by_hash[article.hash].fetched_at:
                                    articles_by_hash[article.hash] = article
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        # Sort by published_at (desc) or fetched_at (desc)
        sorted_articles = sorted(
            articles_by_hash.values(),
            key=lambda a: a.published_at or a.fetched_at,
            reverse=True
        )
        return sorted_articles

    def publish_site(self):
        """Build the entire static site."""
        self.ensure_dirs()
        articles = self.load_all_articles()
        
        # Use timezone-aware UTC
        import datetime as dt
        generated_at = datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        # 1. Generate individual article pages and group for index
        # We'll use a specific order for categories: Reading Material first, then National News
        categories = ["Reading Material", "National News"]
        grouped_articles: Dict[str, List[str]] = {cat: [] for cat in categories}
        grouped_articles["Other"] = []

        for article in articles:
            self.publish_article_page(article, generated_at)
            
            # Prepare data for index item
            date_str = article.published_at[:10] if article.published_at else article.fetched_at[:10]
            excerpt = article.subtitle or (article.content_text[:200] + "..." if article.content_text else "Click to read more.")
            
            item_html = ARTICLE_ITEM_TEMPLATE.substitute(
                hash=article.hash,
                source=article.source.replace("_", " ").upper(),
                date=date_str,
                title=article.title,
                excerpt=excerpt
            )
            
            cat = article.category if article.category in categories else ("Reading Material" if not article.category else "Other")
            if cat not in grouped_articles:
                grouped_articles[cat] = []
            grouped_articles[cat].append(item_html)

        # 2. Generate sections HTML
        sections_html = []
        # Display Reading Material first, then National News
        for cat in ["Reading Material", "National News", "Other"]:
            if grouped_articles.get(cat):
                section_html = SECTION_TEMPLATE.substitute(
                    title=cat,
                    article_items="\n".join(grouped_articles[cat])
                )
                sections_html.append(section_html)

        # 3. Generate index page
        index_html = INDEX_TEMPLATE.substitute(
            base_head=BASE_HEAD,
            sections_html="\n".join(sections_html),
            generated_at=generated_at
        )
        with open(self.site_root / "index.html", "w") as f:
            f.write(index_html)
            
        return len(articles)

    def publish_article_page(self, article: Article, generated_at: str):
        """Generate a single article HTML page."""
        date_str = article.published_at[:10] if article.published_at else article.fetched_at[:10]
        
        author_html = f'<span>By {article.author}</span>' if article.author else ""
        
        # Hero image logic
        hero_html = ""
        if article.image_url:
            caption_html = f'<div class="image-caption">{article.image_caption}</div>' if article.image_caption else ""
            hero_html = f"""
            <div class="hero-image">
                <img src="{article.image_url}" alt="{article.title}">
                {caption_html}
            </div>
            """
        
        # If content_html is empty, provide a placeholder
        content_html = article.content_html
        if not content_html:
            if article.content_text:
                content_html = "".join([f"<p>{p}</p>" for p in article.content_text.split("\n\n")])
            else:
                content_html = "<p>Content currently unavailable. This may be because the article body has not been fetched yet.</p>"

        page_html = ARTICLE_PAGE_TEMPLATE.substitute(
            base_head=BASE_HEAD,
            title=article.title,
            author_html=author_html,
            source=article.source.replace("_", " ").upper(),
            date=date_str,
            hero_html=hero_html,
            content_html=content_html,
            url=article.url,
            generated_at=generated_at
        )
        
        with open(self.content_dir / f"{article.hash}.html", "w") as f:
            f.write(page_html)
