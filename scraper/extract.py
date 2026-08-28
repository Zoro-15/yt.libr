"""
Extraction pipeline coordinator.
Manages raw extraction, saving to data/raw/, logging errors, and optional full pipeline runs.
"""

from pathlib import Path
from typing import Optional

from scraper.config import ScraperConfig
from scraper.merge import merge_sources
from scraper.normalize import normalize_raw_entries
from scraper.output import save_error_log, save_processed_videos, save_raw_extraction
from scraper.utils import (
    CHECK_MARK,
    CROSS_MARK,
    SEP_LINE,
    WARN_MARK,
    bold,
    cyan,
    green,
    print_progress,
    red,
    yellow,
)
from scraper.youtube import extract_youtube_playlist, ExtractionResult


def scrape_source(
    source_name: str,
    config: ScraperConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> ExtractionResult:
    """
    Executes raw metadata extraction for a single playlist source (watch_later or liked).
    Saves output to data/raw/<source>.json.
    """
    display_title = "Watch Later" if source_name == "watch_later" else "Liked Videos"
    print(bold(f"\nExtracting Source: {cyan(display_title)}"))
    if limit:
        print(f"Limit: {cyan(str(limit))} videos")
    if dry_run:
        print(yellow("DRY RUN MODE: Extracted data will NOT be written to disk."))

    def on_progress(current: int, total: Optional[int], success: int, unavail: int, failed: int):
        print_progress(
            current=current,
            total=total,
            success=success,
            unavailable=unavail,
            failed=failed,
        )

    result = extract_youtube_playlist(
        source_name=source_name,
        config=config,
        limit=limit,
        dry_run=dry_run,
        progress_callback=on_progress,
    )

    # Print final line break after progress bar
    print()

    if not dry_run:
        # Save raw JSON
        raw_path = config.watch_later_raw_path if source_name == "watch_later" else config.liked_raw_path
        save_raw_extraction(
            output_path=raw_path,
            source_name=source_name,
            raw_entries=result.entries,
            playlist_title=result.playlist_title,
        )
        print(f"Raw data saved to: {green(str(raw_path))}")

        # Save errors if any
        if result.errors:
            save_error_log(config.errors_log_path, result.errors)
            print(f"Logged {yellow(str(len(result.errors)))} unavailable/error items to {config.errors_log_path}")

    print(f"Summary for {display_title}: "
          f"{green(f'{CHECK_MARK} {result.success_count:,} valid')} | "
          f"{yellow(f'{WARN_MARK} {result.unavailable_count:,} unavailable')} | "
          f"{red(f'{CROSS_MARK} {result.failed_count:,} failed')}")

    return result


def run_merge_pipeline(config: ScraperConfig) -> None:
    """
    Loads data/raw/watch_later.json and data/raw/liked.json,
    normalizes, deduplicates, merges, and writes data/processed/videos.json.
    """
    from scraper.output import load_raw_extraction

    print(bold("\n--- Running Normalization & Source Merge Pipeline ---"))

    wl_raw = load_raw_extraction(config.watch_later_raw_path)
    liked_raw = load_raw_extraction(config.liked_raw_path)

    if not wl_raw and not liked_raw:
        print(red("No raw data found! Run 'yt-library scrape watch-later' and/or 'yt-library scrape liked' first."))
        return

    print(f"Loaded Raw Watch Later entries: {cyan(str(len(wl_raw)))}")
    print(f"Loaded Raw Liked entries:       {cyan(str(len(liked_raw)))}")

    # Normalize
    wl_normalized = normalize_raw_entries(wl_raw, source_name="watch_later")
    liked_normalized = normalize_raw_entries(liked_raw, source_name="liked")

    print(f"Normalized Watch Later records: {green(str(len(wl_normalized)))}")
    print(f"Normalized Liked records:       {green(str(len(liked_normalized)))}")

    # Merge and Deduplicate
    merged_records, summary = merge_sources(wl_normalized, liked_normalized)

    # Save final JSON
    save_processed_videos(
        output_path=config.videos_processed_path,
        records=merged_records,
        schema_version=config.schema_version,
    )

    print(bold("\n=================================================="))
    print(bold(" MERGE COMPLETE"))
    print(bold("=================================================="))
    print(f"Watch Later input:   {summary.total_watch_later:,}")
    print(f"Liked Videos input:  {summary.total_liked:,}")
    print(f"Total raw items:     {summary.total_watch_later + summary.total_liked:,}")
    print(SEP_LINE)
    print(f"Total Unique Videos: {green(f'{summary.total_unique:,}')}")
    print(f"Appearing in Both:   {cyan(f'{summary.overlap_count:,}')}")
    if summary.duplicates_in_watch_later > 0:
        print(f"Duplicate IDs in WL: {yellow(str(summary.duplicates_in_watch_later))}")
    if summary.duplicates_in_liked > 0:
        print(f"Duplicate IDs in LL: {yellow(str(summary.duplicates_in_liked))}")
    print(SEP_LINE)
    print(f"Output: {green(str(config.videos_processed_path))}")
    print(bold("=================================================="))
