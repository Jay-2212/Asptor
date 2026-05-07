"""CLI entry point for the static publishing pipeline."""
import argparse
import sys
from pathlib import Path

from scripts.publish.publisher import Publisher

def main():
    parser = argparse.ArgumentParser(description="Generate the static website.")
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=Path("data/processed"),
        help="Path to the directory containing processed articles (default: data/processed)"
    )
    parser.add_argument(
        "--site-root",
        type=Path,
        default=Path("site"),
        help="Path to the directory where static files will be generated (default: site)"
    )

    args = parser.parse_args()

    # Ensure absolute paths
    processed_root = args.processed_root.absolute()
    site_root = args.site_root.absolute()

    print(f"Publishing site...")
    print(f"  Processed root: {processed_root}")
    print(f"  Site root:      {site_root}")

    try:
        publisher = Publisher(processed_root, site_root)
        count = publisher.publish_site()
        print(f"Done! Published {count} articles.")
    except Exception as e:
        print(f"Error during publishing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
