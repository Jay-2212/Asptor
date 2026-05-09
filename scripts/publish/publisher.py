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
                                if article.hash in articles_by_hash:
                                    article = self.merge_duplicate_article(
                                        articles_by_hash[article.hash], article
                                    )
                                
                                # Keep the latest record, but never lose body content
                                # that was already fetched in an older snapshot.
                                if (
                                    article.hash not in articles_by_hash
                                    or article.fetched_at > articles_by_hash[article.hash].fetched_at
                                ):
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

    @staticmethod
    def article_sort_key(article: Article) -> str:
        """Return the timestamp used for feed ordering."""
        return article.published_at or article.fetched_at

    @staticmethod
    def content_quality_score(article: Article) -> tuple[int, int]:
        """Rank article body quality by preserved paragraph structure."""
        html = article.content_html or ""
        text = article.content_text or ""
        paragraph_count = html.count("<p") + text.count("\n\n")
        return paragraph_count, len(html) + len(text)

    def mix_sources_for_feed(self, articles: List[Article]) -> List[Article]:
        """Interleave sources while keeping each source internally recent-first.

        Many articles discovered in one scheduled run share the same timestamp.
        A plain timestamp sort then falls back to source/file order and creates
        long blocks from one publication. This keeps the feed deterministic but
        rotates across available sources for a livelier reading mix.
        """
        by_source: Dict[str, List[Article]] = {}
        for article in articles:
            by_source.setdefault(article.source, []).append(article)

        for source_articles in by_source.values():
            source_articles.sort(key=self.article_sort_key, reverse=True)

        mixed: List[Article] = []
        while by_source:
            source_names = sorted(
                by_source,
                key=lambda source: (
                    self.article_sort_key(by_source[source][0]),
                    source,
                ),
                reverse=True,
            )
            for source in source_names:
                mixed.append(by_source[source].pop(0))
                if not by_source[source]:
                    del by_source[source]

        return mixed

    @staticmethod
    def merge_duplicate_article(existing: Article, candidate: Article) -> Article:
        """Merge duplicate snapshots while preferring the newest metadata.

        Listing-page snapshots often rediscover an already-seen article with an
        empty body. The full body may exist only on an older enriched record, so
        deduplication must carry that content forward.
        """
        if candidate.fetched_at >= existing.fetched_at:
            base = candidate
            fallback = existing
        else:
            base = existing
            fallback = candidate

        if Publisher.content_quality_score(fallback) > Publisher.content_quality_score(base):
            base.content_html = fallback.content_html
            base.content_text = fallback.content_text

        for field in (
            "author",
            "published_at",
            "image_url",
            "image_caption",
            "subtitle",
            "category",
        ):
            if not getattr(base, field) and getattr(fallback, field):
                setattr(base, field, getattr(fallback, field))

        return base

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
        grouped_articles: Dict[str, List[Article]] = {cat: [] for cat in categories}
        grouped_articles["Other"] = []

        for article in articles:
            self.publish_article_page(article, generated_at)

            cat = article.category if article.category in categories else ("Reading Material" if not article.category else "Other")
            if cat not in grouped_articles:
                grouped_articles[cat] = []
            grouped_articles[cat].append(article)

        # 2. Generate sections HTML
        sections_html = []
        # Display Reading Material first, then National News
        for cat in ["Reading Material", "National News", "Other"]:
            if grouped_articles.get(cat):
                article_items = []
                for article in self.mix_sources_for_feed(grouped_articles[cat]):
                    date_str = article.published_at[:10] if article.published_at else article.fetched_at[:10]
                    excerpt = article.subtitle or (article.content_text[:200] + "..." if article.content_text else "Click to read more.")
                    article_items.append(
                        ARTICLE_ITEM_TEMPLATE.substitute(
                            hash=article.hash,
                            source=article.source.replace("_", " ").upper(),
                            date=date_str,
                            title=article.title,
                            excerpt=excerpt
                        )
                    )
                section_html = SECTION_TEMPLATE.substitute(
                    title=cat,
                    article_items="\n".join(article_items)
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
