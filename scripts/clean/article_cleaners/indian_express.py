"""Article cleaner for Indian Express."""
from __future__ import annotations
from bs4 import BeautifulSoup
import re

class IndianExpressArticleCleaner:
    def clean(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract Author
        author_tag = soup.select_one(".editor, .author, span[itemprop='name']")
        author = author_tag.get_text(strip=True) if author_tag else None
        
        # 2. Extract Date
        date_tag = soup.select_one(".publish-date, .date, time")
        date = date_tag.get_text(strip=True) if date_tag else None
        if not date:
            meta_date = soup.find("meta", property="article:published_time")
            if meta_date:
                date = meta_date.get("content")

        # 3. Extract Hero Image
        image_url = None
        image_caption = None
        hero_container = soup.select_one(".article-img, .featured-image, .hero-image, .custom-caption")
        if hero_container:
            img = hero_container.select_one("img")
            if img:
                # IE often has lazy loading or srcset
                image_url = img.get("data-src") or img.get("src")
                if img.get("srcset"):
                    srcset = img["srcset"].split(",")
                    image_url = srcset[-1].strip().split(" ")[0]
            
            caption_tag = hero_container.select_one("figcaption, .caption, .img-caption")
            if caption_tag:
                image_caption = caption_tag.get_text(strip=True)

        # 4. Clean Article Body
        # Indian Express uses .article-body, #article-body, or .full-details
        container = soup.select_one(".article-body, #article-body, .full-details, .content-article")
        if not container:
            container = soup.find("article")
            
        if container:
            # Remove noise
            noise_selectors = [
                ".ad-container", ".related-articles", ".also-read", 
                ".social-sharing", ".newsletter-box", ".tags",
                "script", "style", "aside", "nav", "iframe", ".ie-exclusive",
                ".ie-ie-share", ".google-preferred", ".share-box-n", ".share-options",
                ".article-button-wrap", ".post-info", ".article-publish-date"
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
