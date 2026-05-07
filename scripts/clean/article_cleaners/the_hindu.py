"""Article cleaner for The Hindu."""
from __future__ import annotations
from bs4 import BeautifulSoup
import re

class TheHinduArticleCleaner:
    def __init__(
        self,
        source_name: str = "the_hindu_opinion",
        article_path_pattern: str = "/opinion/",
    ) -> None:
        self.source_name = source_name
        self._article_path_pattern = article_path_pattern

    def clean(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract Author
        # The Hindu uses span.author-name or links with author-name class
        author_tag = soup.select_one("span.author-name, a.author-name, .author-name, .author")
        author = author_tag.get_text(strip=True) if author_tag else None
        
        # 2. Extract Date
        # Typically in p.publish-time or meta tags
        date_tag = soup.select_one("p.publish-time, span.publish-date, .publish-date, .date")
        date = date_tag.get_text(strip=True) if date_tag else None
        if not date:
            meta_date = soup.find("meta", property="article:published_time")
            if meta_date:
                date = meta_date.get("content")

        # 3. Extract Hero Image
        image_url = None
        image_caption = None
        # Look for the lead image container
        hero_container = soup.select_one(".article-lead-img, .hero-image, .lead-img, picture.article-picture")
        if hero_container:
            # Try to get high-res from source srcset
            source = hero_container.select_one("source")
            if source and source.get("srcset"):
                # Usually comma separated: "url1 1x, url2 2x" -> get the last one
                srcset = source["srcset"].split(",")
                image_url = srcset[-1].strip().split(" ")[0]
            else:
                img = hero_container.select_one("img")
                if img:
                    image_url = img.get("src")
            
            # Caption
            caption_tag = hero_container.select_one("figcaption, .caption, .img-caption, .article-img-caption")
            if caption_tag:
                image_caption = caption_tag.get_text(strip=True)

        # 4. Clean Article Body
        # The Hindu uses div.article-body, div.article-content, or .articlebodycontent
        container = soup.select_one("div.article-body, div.article-content, .articlebodycontent, [id^='content-body-']")
        if not container:
            container = soup.find("article")
            
        if container:
            # Create a copy to avoid modifying original soup if needed, but here we decompose
            # Remove noise
            noise_selectors = [
                ".ad-container", ".related-topics-container", ".also-read", 
                ".social-share", ".subscription-container", ".banner-container",
                "script", "style", "aside", "nav", "iframe", ".premium-banner",
                ".article-exclusive", ".social-share-container", ".comments-container",
                ".author-box", ".tags-container", ".related-articles-container",
                ".article-footer", ".share-icons", ".trending-container",
                ".related-topics-list", ".read-comment-btn", ".print-btn",
                "#read-comments", ".print-article", ".comment-btn"
            ]
            for selector in noise_selectors:
                for tag in container.select(selector):
                    tag.decompose()
            
            content_html = str(container)
            content_text = container.get_text(separator="\n", strip=True)
        else:
            content_html = ""
            content_text = ""

        return {
            "content_html": content_html,
            "content_text": content_text,
            "author": author,
            "date": date,
            "image_url": image_url,
            "image_caption": image_caption
        }
