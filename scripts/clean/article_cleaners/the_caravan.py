"""Article cleaner for The Caravan."""
from __future__ import annotations
from bs4 import BeautifulSoup
import re

class TheCaravanArticleCleaner:
    def clean(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract Author
        author_tag = soup.select_one(".usp-dya8f7, .widget_author, .author-name")
        author = author_tag.get_text(strip=True) if author_tag else None
        
        # 2. Extract Date
        date_tag = soup.select_one(".usp-djrphm, .date, time")
        date = date_tag.get_text(strip=True) if date_tag else None

        # 3. Extract Hero Image
        image_url = None
        image_caption = None
        # Caravan uses figure.cover_figure_element or .photo_wrapper
        hero_container = soup.select_one("figure.cover_figure_element, .photo_wrapper, .featured-image")
        if hero_container:
            img = hero_container.select_one("img")
            if img:
                image_url = img.get("src")
                if not image_url.startswith("http"):
                    image_url = "https:" + image_url
            
            caption_tag = hero_container.select_one("figcaption, .article_cover_caption")
            if caption_tag:
                image_caption = caption_tag.get_text(strip=True)

        # 4. Clean Article Body
        # The Caravan uses .article_content (usp-ozzp8u)
        container = soup.select_one(".article_content, .story_details, .story-content, .article-body")
        if not container:
            container = soup.find("article")
            
        if container:
            # Remove noise
            noise_selectors = [
                ".usp-3km52c", # Subscription prompts
                ".ad-container", ".related-stories", ".social-sharing", 
                ".newsletter-signup", ".tags-list", ".paywall-overlay",
                "script", "style", "aside", "nav", "iframe", ".subscriber-only",
                ".article-footer", ".share-buttons", ".more-from-caravan",
                ".usp-4ixkpp" # Footer in article
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
