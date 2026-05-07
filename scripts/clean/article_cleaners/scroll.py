"""Article cleaner for Scroll.in."""
from __future__ import annotations
from bs4 import BeautifulSoup
import re

class ScrollArticleCleaner:
    def clean(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract Author
        author_tag = soup.select_one("address a[rel='author'], meta[name='author']")
        if author_tag and author_tag.name == "meta":
            author = author_tag.get("content")
        else:
            author = author_tag.get_text(strip=True) if author_tag else None
        
        # 2. Extract Date
        date_tag = soup.select_one("time.article-published-time, meta[name='dcterms.created']")
        if date_tag and date_tag.name == "meta":
            date = date_tag.get("content")
        else:
            date = date_tag.get_text(strip=True) if date_tag else None

        # 3. Extract Hero Image
        image_url = None
        image_caption = None
        hero_container = soup.select_one("figure.featured-image, .featured-image")
        if hero_container:
            img = hero_container.select_one("img")
            if img:
                image_url = img.get("src")
                if img.get("srcset"):
                    srcset = img["srcset"].split(",")
                    image_url = srcset[-1].strip().split(" ")[0]
            
            caption_tag = hero_container.select_one("figcaption.featured-image-caption, .caption")
            if caption_tag:
                image_caption = caption_tag.get_text(strip=True)

        # 4. Clean Article Body
        # Scroll uses #article-contents
        container = soup.select_one("div#article-contents, .article-body, article")
        if container:
            # Remove noise
            noise_selectors = [
                ".mail-us-section", ".article-tags-list", ".below-article-share-block", 
                ".share-bar-mobile", ".ad-container", ".newsletter-signup",
                "script", "style", "aside", "nav", "iframe"
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
