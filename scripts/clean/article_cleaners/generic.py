"""Generic fallback article cleaner."""
from __future__ import annotations

from bs4 import BeautifulSoup


def clean_article(html: str) -> dict:
    """Extract content and metadata using generic heuristics.
    
    Returns:
        dict: {content_html, content_text, author, date, image_url, image_caption}
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Heuristics for metadata
    author = ""
    author_tag = soup.find("meta", attrs={"name": "author"})
    if author_tag:
        author = author_tag.get("content", "")
    
    date = ""
    date_tag = soup.find("meta", property="article:published_time")
    if date_tag:
        date = date_tag.get("content", "")

    image_url = ""
    image_tag = soup.find("meta", property="og:image")
    if image_tag:
        image_url = image_tag.get("content", "")

    # Try common article containers
    selectors = [
        "article",
        ".article-body",
        ".post-content",
        ".entry-content",
        "#article-body",
        "#content-body",
        "main",
    ]
    
    container = None
    for selector in selectors:
        if selector.startswith("."):
            container = soup.find(class_=selector[1:])
        elif selector.startswith("#"):
            container = soup.find(id=selector[1:])
        else:
            container = soup.find(selector)
            
        if container:
            break
            
    if not container:
        container = soup.find("body")
        
    if not container:
        return {
            "content_html": "", "content_text": "", "author": author, 
            "date": date, "image_url": image_url, "image_caption": ""
        }
        
    # Clean up
    for tag in container(["script", "style", "aside", "nav", "header", "footer", "iframe"]):
        tag.decompose()
        
    content_html = str(container)
    content_text = container.get_text(separator="\n", strip=True)
    
    return {
        "content_html": content_html,
        "content_text": content_text,
        "author": author,
        "date": date,
        "image_url": image_url,
        "image_caption": ""
    }
