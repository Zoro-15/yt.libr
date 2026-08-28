"""
Extraction pipeline coordinator.
Manages raw extraction from Watch Later, Liked Videos, User Playlists, and custom Playlists,
saving to data/raw/, logging errors, and executing the full normalization & merge pipeline.
"""

from pathlib import Path
from typing import Dict, List, Optional

from scraper.config import ScraperConfig
from scraper.merge import merge_sources
from scraper.normalize import (
    PlaylistRecord,
    VideoRecord,
    extract_canonical_playlist_id,
    normalize_playlist_info,
    normalize_raw_entries,
)
from scraper.output import (
    load_raw_extraction,
    load_raw_playlists_directory,
    load_raw_playlists_index,
    save_error_log,
    save_processed_playlists,
    save_processed_videos,
    save_raw_extraction,
    save_raw_playlists_index,
)
from scraper.utils import (
    CHECK_MARK,
    CROSS_MARK,
    SEP_LINE,
    WARN_MARK,
    bold,
    cyan,
    dim,
    green,
    print_progress,
    red,
    yellow,
)
from scraper.youtube import (
    discover_user_playlists,
    extract_youtube_playlist,
    ExtractionResult,
)


def scrape_source(
    source_name: str,
    config: ScraperConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> ExtractionResult:
    """
    Executes raw metadata extraction for a built-in source (watch_later or liked).
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
        source_name_or_url=source_name,
        config=config,
        limit=limit,
        dry_run=dry_run,
        progress_callback=on_progress,
    )

    print()

    if not dry_run and result.entries:
        raw_path = config.watch_later_raw_path if source_name == "watch_later" else config.liked_raw_path
        save_raw_extraction(
            output_path=raw_path,
            source_name=source_name,
            raw_entries=result.entries,
            playlist_title=result.playlist_title,
            playlist_id=result.playlist_id,
            description=result.playlist_description,
            channel=result.channel_name,
            channel_id=result.channel_id,
        )
        print(f"Raw data saved to: {green(str(raw_path))}")

    if result.errors:
        save_error_log(config.errors_log_path, result.errors)
        print(f"Logged {yellow(str(len(result.errors)))} unavailable/error items to {config.errors_log_path}")

    print(f"Summary for {display_title}: "
          f"{green(f'{CHECK_MARK} {result.success_count:,} valid')} | "
          f"{yellow(f'{WARN_MARK} {result.unavailable_count:,} unavailable')} | "
          f"{red(f'{CROSS_MARK} {result.failed_count:,} failed')}")

    return result


def scrape_single_playlist(
    playlist_id_or_url: str,
    config: ScraperConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> ExtractionResult:
    """
    Extracts all metadata and embedded videos from a specific playlist.
    Saves to data/raw/playlists/<playlist_id>.json.
    Gracefully skips unviewable mix playlists without breaking pipeline.
    """
    pid = extract_canonical_playlist_id(playlist_id_or_url, playlist_id_or_url) or playlist_id_or_url
    print(bold(f"\nExtracting Playlist: {cyan(pid)}"))
    if limit:
        print(f"Limit: {cyan(str(limit))} videos")

    def on_progress(current: int, total: Optional[int], success: int, unavail: int, failed: int):
        print_progress(
            current=current,
            total=total,
            success=success,
            unavailable=unavail,
            failed=failed,
        )

    result = extract_youtube_playlist(
        source_name_or_url=playlist_id_or_url,
        config=config,
        limit=limit,
        dry_run=dry_run,
        progress_callback=on_progress,
    )

    if result.total_processed > 0:
        print()

    if result.success_count == 0 and result.failed_count > 0:
        print(yellow(f"{WARN_MARK} Playlist '{pid}' is unviewable or dynamic mix. Skipped gracefully."))
        if result.errors:
            save_error_log(config.errors_log_path, result.errors)
        return result

    if not dry_run and result.entries:
        raw_path = config.playlists_raw_dir / f"{result.playlist_id}.json"
        save_raw_extraction(
            output_path=raw_path,
            source_name=f"playlist:{result.playlist_id}",
            raw_entries=result.entries,
            playlist_title=result.playlist_title,
            playlist_id=result.playlist_id,
            description=result.playlist_description,
            channel=result.channel_name,
            channel_id=result.channel_id,
        )
        print(f"Playlist saved to: {green(str(raw_path))}")

    if result.errors:
        save_error_log(config.errors_log_path, result.errors)

    print(f"Summary for '{result.playlist_title}': "
          f"{green(f'{CHECK_MARK} {result.success_count:,} valid videos')} | "
          f"{yellow(f'{WARN_MARK} {result.unavailable_count:,} unavailable')}")

    return result


def scrape_user_playlists(
    config: ScraperConfig,
    playlist_limit: Optional[int] = None,
    video_limit: Optional[int] = None,
    dry_run: bool = False,
) -> List[ExtractionResult]:
    """
    Discovers all user playlists from the YouTube account and extracts each one.
    Resilient: an error in one playlist will never interrupt the others.
    """
    print(bold("\n--- Discovering User Playlists ---"))
    discovered = discover_user_playlists(config, limit=playlist_limit)

    if not discovered:
        print(yellow("No custom user playlists found in feed, or cookies do not have playlist permissions."))
        return []

    print(f"Found {green(str(len(discovered)))} user playlist(s):")
    for idx, pl in enumerate(discovered, 1):
        print(f"  {idx:2d}. {cyan(pl['title'])} ({dim(pl['id'])})")

    if not dry_run:
        save_raw_playlists_index(config.playlists_index_raw_path, discovered)

    results: List[ExtractionResult] = []
    for pl in discovered:
        try:
            res = scrape_single_playlist(
                playlist_id_or_url=pl["id"],
                config=config,
                limit=video_limit,
                dry_run=dry_run,
            )
            results.append(res)
        except Exception as err:
            print(yellow(f"{WARN_MARK} Unexpected error extracting playlist '{pl.get('id')}': {err}"))
            save_error_log(config.errors_log_path, [{
                "video_id": pl.get("id", "unknown"),
                "source": f"playlist:{pl.get('id', 'unknown')}",
                "error": str(err),
            }])

    return results


def run_merge_pipeline(config: ScraperConfig) -> None:
    """
    Loads Watch Later, Liked Videos, and all custom Playlists from data/raw/,
    normalizes, deduplicates, merges, and writes:
      - data/processed/videos.json
      - data/processed/playlists.json
    """
    print(bold("\n--- Running Normalization & Multi-Source Merge Pipeline ---"))

    wl_raw = load_raw_extraction(config.watch_later_raw_path)
    liked_raw = load_raw_extraction(config.liked_raw_path)
    raw_playlists = load_raw_playlists_directory(config.playlists_raw_dir)

    if not wl_raw and not liked_raw and not raw_playlists:
        print(red("No raw data found! Run extraction commands first."))
        return

    print(f"Loaded Raw Watch Later entries: {cyan(str(len(wl_raw)))}")
    print(f"Loaded Raw Liked entries:       {cyan(str(len(liked_raw)))}")
    print(f"Loaded Raw Custom Playlists:    {cyan(str(len(raw_playlists)))}")

    # Normalize Watch Later and Liked
    wl_normalized = normalize_raw_entries(wl_raw, source_name="watch_later")
    liked_normalized = normalize_raw_entries(liked_raw, source_name="liked")

    # Normalize Custom Playlists
    custom_playlist_records: Dict[str, List[VideoRecord]] = {}
    playlists_info: List[PlaylistRecord] = []

    for raw_pl in raw_playlists:
        pid = raw_pl.get("playlist_id") or raw_pl.get("id") or "custom_playlist"
        title = raw_pl.get("playlist_title") or raw_pl.get("title") or pid
        entries = raw_pl.get("entries") or []

        if not entries:
            continue

        normalized_entries = normalize_raw_entries(
            entries,
            source_name=f"playlist:{pid}",
            playlist_id=pid,
            playlist_title=title,
        )
        custom_playlist_records[pid] = normalized_entries

        vids = [r.video_id for r in normalized_entries]
        pl_info = normalize_playlist_info(raw_pl, video_ids=vids)
        if pl_info:
            playlists_info.append(pl_info)

    # Merge and Deduplicate
    merged_videos, merged_playlists, summary = merge_sources(
        watch_later_records=wl_normalized,
        liked_records=liked_normalized,
        custom_playlist_records=custom_playlist_records,
        playlists_info=playlists_info,
    )

    # Save final JSONs
    save_processed_videos(
        output_path=config.videos_processed_path,
        records=merged_videos,
        schema_version=config.schema_version,
    )

    if merged_playlists:
        save_processed_playlists(
            output_path=config.playlists_processed_path,
            playlists=merged_playlists,
            schema_version=config.schema_version,
        )

    print(bold("\n=================================================="))
    print(bold(" MERGE COMPLETE"))
    print(bold("=================================================="))
    print(f"Watch Later input:    {summary.total_watch_later:,}")
    print(f"Liked Videos input:   {summary.total_liked:,}")
    print(f"Custom Playlists:     {summary.total_custom_playlists:,}")
    print(f"Playlist video refs:  {summary.total_playlist_videos:,}")
    print(SEP_LINE)
    print(f"Total Unique Videos:  {green(f'{summary.total_unique:,}')}")
    print(f"Overlapping Videos:   {cyan(f'{summary.overlap_count:,}')}")
    print(SEP_LINE)
    print(f"Processed Videos:     {green(str(config.videos_processed_path))}")
    if merged_playlists:
        print(f"Processed Playlists:  {green(str(config.playlists_processed_path))}")
    print(bold("=================================================="))
