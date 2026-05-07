"""Article body cleaner for Fifty Two."""
from __future__ import annotations

import re
from bs4 import BeautifulSoup


class FiftyTwoArticleCleaner:
    """Cleaner for Fifty Two articles."""

    def clean(self, html: str) -> dict:
        """Extract content and metadata from Fifty Two article HTML.
        
        Returns:
            dict: {content_html, content_text, author, date, image_url, image_caption}
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract Author
        author = ""
        author_tag = soup.select_one(".story-info__author")
        if author_tag:
            author = author_tag.get_text(separator=" ", strip=True)
        else:
            # Fallback to meta
            meta_author = soup.find("meta", attrs={"name": "author"})
            if meta_author:
                author = meta_author.get("content", "")

        # 2. Extract Publication Date
        date = ""
        date_tag = soup.select_one(".story-info__date")
        if date_tag:
            date = date_tag.get_text(strip=True)
            
        # 3. Extract High-Resolution Image
        image_url = ""
        image_caption = ""
        banner_img = soup.select_one(".story-banner__image img")
        if banner_img:
            # Try to get high-res from srcset if available
            picture = banner_img.find_parent("picture")
            if picture:
                sources = picture.find_all("source")
                max_width = 0
                for source in sources:
                    srcset = source.get("srcset", "")
                    # Prismic URLs often have &w=... parameter
                    match = re.search(r"&w=(\d+)", srcset)
                    if match:
                        width = int(match.group(1))
                        if width > max_width:
                            max_width = width
                            image_url = srcset.split(" ")[0]
            
            # Fallback to src if image_url not set or if src is larger
            src = banner_img.get("src", "")
            match_src = re.search(r"&w=(\d+)", src)
            if match_src:
                src_width = int(match_src.group(1))
                if src_width > max_width:
                    image_url = src
            elif not image_url:
                image_url = src
                
            image_caption = banner_img.get("alt", "")

        # 4. Identify noise selectors and remove them
        noise_selectors = [
            ".site-header",
            ".site-footer",
            ".story-sidebar",
            ".story-next",
            ".story-footer",
            ".subscribe-bar",
            ".svg-separator",
            ".reading-progress-bar",
            ".inline-svg-wrapper",
            "#sidebar-right",
            ".b-sidebar-outer",
            "script",
            "style",
            ".story-info", # Removed as we already extracted it
        ]
        
        # We'll work on a copy for the body
        body_soup = BeautifulSoup(html, "html.parser")
        # Find the main article container
        article = body_soup.select_one("article.story")
        if not article:
            article = body_soup.find("body")

        if article:
            for selector in noise_selectors:
                for noise in article.select(selector):
                    noise.decompose()
            
            # Additional clean up: remove empty divs/sections that might be left
            for div in article.find_all("div", recursive=False):
                if not div.get_text(strip=True) and not div.find("img"):
                    div.decompose()

            content_html = str(article)
            content_text = article.get_text(separator="\n", strip=True)
        else:
            content_html = ""
            content_text = ""

        return {
            "content_html": content_html,
            "content_text": content_text,
            "author": author,
            "date": date,
            "image_url": image_url,
            "image_caption": image_caption,
        }
