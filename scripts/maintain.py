"""Maintainer script for Asptor: Runs the pipeline and audits the quality."""
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Maintainer")

def run_command(command: str):
    logger.info(f"Executing: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with exit code {result.returncode}")
        logger.error(result.stderr)
        return False
    return True

def audit_data(processed_root: Path):
    logger.info("Auditing processed data...")
    total_articles = 0
    empty_content = 0
    missing_images = 0
    sources_found = set()

    for source_dir in processed_root.iterdir():
        if not source_dir.is_dir():
            continue
        sources_found.add(source_dir.name)
        for json_file in source_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    articles = json.load(f)
                for a in articles:
                    total_articles += 1
                    if not a.get("content_html") or len(a["content_html"]) < 100:
                        empty_content += 1
                    if not a.get("image_url"):
                        missing_images += 1
            except Exception as e:
                logger.error(f"Error reading {json_file}: {e}")

    logger.info(f"Audit Summary:")
    logger.info(f"  Total Articles: {total_articles}")
    logger.info(f"  Sources: {', '.join(sorted(sources_found))}")
    logger.info(f"  Empty/Short Content: {empty_content}")
    logger.info(f"  Missing Hero Images: {missing_images}")
    
    return {
        "total": total_articles,
        "empty": empty_content,
        "missing_images": missing_images
    }

def main():
    logger.info("Starting Asptor Maintenance Run...")
    
    # 1. Run Pipeline
    pipeline_steps = [
        "python3 -m scripts.fetch.run_fetch --raw-root data/raw",
        "python3 -m scripts.clean.run_clean --raw-root data/raw --processed-root data/processed",
        "python3 -m scripts.diff.run_diff --processed-root data/processed --state-root data/state --diff-root data/diff",
        "python3 -m scripts.clean.run_full_clean --processed-root data/processed --diff-root data/diff --limit 10",
        "python3 -m scripts.publish.run_publish --processed-root data/processed --site-root site"
    ]
    
    for step in pipeline_steps:
        if not run_command(step):
            logger.error("Pipeline interrupted due to error.")
            break
            
    # 2. Audit
    stats = audit_data(Path("data/processed"))
    
    # 3. Final Report
    report_path = Path("MAINTENANCE_REPORT.md")
    with open(report_path, "w") as f:
        f.write(f"# Asptor Maintenance Report\n\n")
        f.write(f"**Run Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Statistics\n")
        f.write(f"- **Total Articles Discovered:** {stats['total']}\n")
        f.write(f"- **Empty/Short Content:** {stats['empty']}\n")
        f.write(f"- **Missing Hero Images:** {stats['missing_images']}\n\n")
        f.write(f"## Status\n")
        if stats['empty'] > stats['total'] * 0.5:
            f.write(f"⚠️ **Warning:** More than 50% of articles have empty content. Check cleaners.\n")
        else:
            f.write(f"✅ **System Healthy:** Pipeline is functioning within expected parameters.\n")

    logger.info(f"Maintenance complete. Report saved to {report_path}")

if __name__ == "__main__":
    main()
