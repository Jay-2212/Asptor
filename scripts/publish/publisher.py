"""Core publishing logic for generating the static site."""
import json
import os
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, List, Optional

from scripts.clean.schema import Article

# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------

INDEX_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asptor - Clean Reading</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background-color: #f9f9f9;
        }
        header {
            margin-bottom: 3rem;
            border-bottom: 2px solid #eee;
            padding-bottom: 1rem;
        }
        h1 { margin: 0; color: #1a1a1a; }
        .subtitle { color: #666; font-style: italic; }
        .article-list { list-style: none; padding: 0; }
        .article-item {
            background: white;
            margin-bottom: 1.5rem;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .article-item:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .article-link { text-decoration: none; color: inherit; display: block; }
        .article-title { margin: 0 0 0.5rem 0; color: #0066cc; font-size: 1.4rem; }
        .article-meta { font-size: 0.9rem; color: #888; margin-bottom: 0.5rem; }
        .article-excerpt { font-size: 1rem; color: #555; }
        footer { margin-top: 4rem; text-align: center; color: #999; font-size: 0.8rem; }
    </style>
</head>
<body>
    <header>
        <h1>Asptor</h1>
        <p class="subtitle">Clean, ad-free reading from quality sources.</p>
    </header>
    <main>
        <ul class="article-list">
            ${article_items}
        </ul>
    </main>
    <footer>
        <p>Generated on ${generated_at} • <a href="https://github.com/jaybharti/asptor">GitHub</a></p>
    </footer>
</body>
</html>
""")

ARTICLE_ITEM_TEMPLATE = Template("""
            <li class="article-item">
                <a href="content/${hash}.html" class="article-link">
                    <div class="article-meta">${source} • ${date}</div>
                    <h2 class="article-title">${title}</h2>
                    <p class="article-excerpt">${excerpt}</p>
                </a>
            </li>
""")

ARTICLE_PAGE_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} - Asptor</title>
    <style>
        body {
            font-family: Georgia, serif;
            line-height: 1.8;
            color: #1a1a1a;
            max-width: 700px;
            margin: 0 auto;
            padding: 2rem 1rem;
            background-color: #fff;
        }
        header { margin-bottom: 3rem; }
        .back-link { font-family: sans-serif; text-decoration: none; color: #0066cc; font-size: 0.9rem; }
        h1 { font-size: 2.5rem; line-height: 1.2; margin: 1rem 0 0.5rem 0; }
        .subtitle { font-size: 1.2rem; color: #666; margin-bottom: 1rem; line-height: 1.4; }
        .meta { font-family: sans-serif; color: #888; font-size: 0.9rem; margin-bottom: 2rem; border-bottom: 1px solid #eee; padding-bottom: 1rem; }
        .content { font-size: 1.15rem; }
        .content p { margin-bottom: 1.5rem; }
        .source-link { display: inline-block; margin-top: 3rem; font-family: sans-serif; background: #eee; padding: 0.5rem 1rem; border-radius: 4px; text-decoration: none; color: #333; }
        footer { margin-top: 5rem; text-align: center; color: #999; font-size: 0.8rem; font-family: sans-serif; }
    </style>
</head>
<body>
    <header>
        <a href="../index.html" class="back-link">← Back to Index</a>
        <h1>${title}</h1>
        ${subtitle_html}
        <div class="meta">
            ${author_html}
            ${source} • ${date}
        </div>
    </header>
    <main class="content">
        ${content_html}
    </main>
    <a href="${url}" class="source-link" target="_blank" rel="noopener">Read original at ${source} →</a>
    <footer>
        <p>Published on Asptor • Generated on ${generated_at}</p>
    </footer>
</body>
</html>
""")

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
        
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        # 1. Generate individual article pages
        article_items_html = []
        for article in articles:
            self.publish_article_page(article, generated_at)
            
            # Prepare data for index item
            date_str = article.published_at[:10] if article.published_at else article.fetched_at[:10]
            excerpt = article.subtitle or (article.content_text[:150] + "..." if article.content_text else "Click to read more.")
            
            item_html = ARTICLE_ITEM_TEMPLATE.substitute(
                hash=article.hash,
                source=article.source.replace("_", " ").title(),
                date=date_str,
                title=article.title,
                excerpt=excerpt
            )
            article_items_html.append(item_html)

        # 2. Generate index page
        index_html = INDEX_TEMPLATE.substitute(
            article_items="\n".join(article_items_html),
            generated_at=generated_at
        )
        with open(self.site_root / "index.html", "w") as f:
            f.write(index_html)
            
        return len(articles)

    def publish_article_page(self, article: Article, generated_at: str):
        """Generate a single article HTML page."""
        date_str = article.published_at[:10] if article.published_at else article.fetched_at[:10]
        
        subtitle_html = f'<p class="subtitle">{article.subtitle}</p>' if article.subtitle else ""
        author_html = f'By {article.author} • ' if article.author else ""
        
        # If content_html is empty, provide a placeholder or just use title
        content_html = article.content_html
        if not content_html:
            if article.content_text:
                content_html = "".join([f"<p>{p}</p>" for p in article.content_text.split("\n\n")])
            else:
                content_html = "<p>Content currently unavailable. Please visit the original source.</p>"

        page_html = ARTICLE_PAGE_TEMPLATE.substitute(
            title=article.title,
            subtitle_html=subtitle_html,
            author_html=author_html,
            source=article.source.replace("_", " ").title(),
            date=date_str,
            content_html=content_html,
            url=article.url,
            generated_at=generated_at
        )
        
        with open(self.content_dir / f"{article.hash}.html", "w") as f:
            f.write(page_html)
