"""Processor to fetch and clean full article bodies."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

from scripts.fetch.fetcher import fetch_with_retries
from scripts.clean.schema import Article
from scripts.clean.article_cleaners.the_hindu import TheHinduArticleCleaner
from scripts.clean.article_cleaners.indian_express import IndianExpressArticleCleaner
from scripts.clean.article_cleaners.the_caravan import TheCaravanArticleCleaner
from scripts.clean.article_cleaners.fifty_two import FiftyTwoArticleCleaner
from scripts.clean.article_cleaners.generic import clean_article as generic_clean

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FullArticleProcessor:
    def __init__(self, processed_root: Path, diff_root: Path):
        self.processed_root = processed_root
        self.diff_root = diff_root
        self.cleaners = {
            "the_hindu_opinion": TheHinduArticleCleaner(),
            "the_hindu_national": TheHinduArticleCleaner(source_name="the_hindu_national", article_path_pattern="/news/national/"),
            "indian_express_explained": IndianExpressArticleCleaner(),
            "the_caravan": TheCaravanArticleCleaner(),
            "fifty_two": FiftyTwoArticleCleaner(),
        }

    def get_cleaner(self, source_name: str):
        return self.cleaners.get(source_name)

    def process_all(self, limit: int = 5):
        """Fetch and clean full bodies for articles found in diff_root."""
        if not self.diff_root.exists():
            logger.info("No diff files found. Skipping full content fetch.")
            return

        for source_dir in self.diff_root.iterdir():
            if not source_dir.is_dir():
                continue
            
            source_name = source_dir.name
            logger.info(f"Processing new articles for: {source_name}")
            
            for diff_file in source_dir.glob("*.json"):
                self.process_diff_file(diff_file, source_name, limit)

    def process_diff_file(self, diff_file: Path, source_name: str, limit: int):
        try:
            with open(diff_file, "r") as f:
                articles_data = json.load(f)
            
            if not isinstance(articles_data, list) or not articles_data:
                return

            logger.info(f"  Enriching {len(articles_data)} articles in {diff_file.name}")
            
            count = 0
            for i, data in enumerate(articles_data):
                if count >= limit:
                    break
                
                article = Article.from_dict(data)
                
                logger.info(f"    Fetching: {article.title}")
                try:
                    raw_html = fetch_with_retries(url=article.url, max_attempts=2)
                    cleaner = self.get_cleaner(source_name)
                    result = cleaner.clean(raw_html) if cleaner else generic_clean(raw_html)
                    
                    # Update fields
                    article.content_html = result.get("content_html", "")
                    article.content_text = result.get("content_text", "")
                    article.author = result.get("author") or article.author
                    article.image_url = result.get("image_url") or article.image_url
                    article.image_caption = result.get("image_caption", "")
                    
                    articles_data[i] = article.to_dict()
                    
                    # Also update the corresponding article in data/processed/
                    self.update_processed_record(article, source_name)
                    
                    count += 1
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"      Error: {e}")

            with open(diff_file, "w") as f:
                json.dump(articles_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error processing {diff_file}: {e}")

    def update_processed_record(self, enriched_article: Article, source_name: str):
        """Update the article in processed_root so history is also enriched."""
        source_proc_dir = self.processed_root / source_name
        if not source_proc_dir.exists():
            return

        for proc_file in source_proc_dir.glob("*.json"):
            try:
                with open(proc_file, "r") as f:
                    data = json.load(f)
                
                updated = False
                for i, item in enumerate(data):
                    if item.get("hash") == enriched_article.hash:
                        data[i] = enriched_article.to_dict()
                        updated = True
                
                if updated:
                    with open(proc_file, "w") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except:
                continue

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument("--diff-root", type=Path, default=Path("data/diff"))
    parser.add_argument("--limit", type=int, default=10, help="Limit articles per source per run")
    args = parser.parse_args()
    
    processor = FullArticleProcessor(args.processed_root, args.diff_root)
    processor.process_all(limit=args.limit)
