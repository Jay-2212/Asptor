"""Article body cleaner for Fifty Two."""
import json
import re
from bs4 import BeautifulSoup


class FiftyTwoArticleCleaner:
    """Cleaner for Fifty Two articles."""

    @staticmethod
    def _extract_dom_body(soup: BeautifulSoup) -> tuple[str, str]:
        """Extract paragraph-level body content from the rendered article DOM."""
        body_parts = soup.select(".story-intro__text, .paragraph__text, .drop-cap__other-text")
        if not body_parts:
            body_parts = soup.select("article p, main p")

        paragraphs = []
        seen = set()

        for part in body_parts:
            text = part.get_text(" ", strip=True)
            if not text or text in seen:
                continue
            seen.add(text)
            for tag in [part, *part.find_all(True)]:
                tag.attrs.pop("style", None)
            paragraphs.append(part)

        if not paragraphs:
            return "", ""

        content_html = "".join(str(p) for p in paragraphs)
        content_text = "\n\n".join(p.get_text(" ", strip=True) for p in paragraphs)
        return content_html, content_text

    def clean(self, html: str) -> dict:
        """Extract content and metadata from Fifty Two article HTML.
        
        Returns:
            dict: {content_html, content_text, author, date, image_url, image_caption}
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Try to extract from JSON-LD first (most complete for 52)
        title = None
        author = None
        date = None
        content_text = ""
        content_html = ""
        image_url = None
        
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0]
                
                title = data.get("headline") or data.get("name")
                body = data.get("articleBody", "")
                if body:
                    content_text = body
                    # Convert plain text body to basic HTML paragraphs
                    paragraphs = re.split(r"\n{2,}", content_text)
                    content_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
                
                author_data = data.get("author")
                if isinstance(author_data, dict):
                    author = author_data.get("name")
                elif isinstance(author_data, list):
                    author = author_data[0].get("name")
                
                date = data.get("datePublished")
                image_data = data.get("image")
                if isinstance(image_data, list) and image_data:
                    image_url = image_data[0]
                elif isinstance(image_data, str):
                    image_url = image_data
            except Exception:
                pass

        # 2. Fallback or complement with DOM parsing
        if not author:
            author_tag = soup.select_one(".story-info__author")
            author = author_tag.get_text(separator=" ", strip=True) if author_tag else ""

        if not date:
            date_tag = soup.select_one(".story-info__date")
            date = date_tag.get_text(strip=True) if date_tag else ""
            
        if not image_url:
            banner_img = soup.select_one(".story-banner__image img, .story-header__image img")
            if banner_img:
                image_url = banner_img.get("src", "")
                
        dom_html, dom_text = self._extract_dom_body(soup)
        if dom_html:
            content_html = dom_html
            content_text = dom_text

        return {
            "title": title,
            "content_html": content_html,
            "content_text": content_text,
            "author": author,
            "date": date,
            "image_url": image_url,
            "image_caption": None,
        }
