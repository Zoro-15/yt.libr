"""
YouTube extraction module.
Wraps yt-dlp to extract playlist metadata (Watch Later and Liked Videos)
without downloading media, with support for batching, limits, progress tracking, and checkpoints.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from scraper.config import ScraperConfig
from scraper.normalize import extract_canonical_video_id
from scraper.utils import iso_now, print_progress


PLAYLIST_URL_MAP = {
    "watch_later": "https://www.youtube.com/playlist?list=WL",
    "liked": "https://www.youtube.com/playlist?list=LL",
}


@dataclass
class ExtractionResult:
    source_name: str
    playlist_title: str
    entries: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_processed: int
    success_count: int
    unavailable_count: int
    failed_count: int


def is_entry_unavailable(entry: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Checks if a raw entry is marked as private, deleted, or unavailable.
    """
    if entry is None:
        return True, "Null entry returned by YouTube"

    title = (entry.get("title") or "").strip().lower()
    if "[deleted video]" in title:
        return True, "Deleted video"
    if "[private video]" in title:
        return True, "Private video"
    if title == "unavailable video" or title == "video unavailable":
        return True, "Video unavailable"

    availability = (entry.get("availability") or "").lower()
    if availability in ("deleted", "private", "unavailable", "needs_auth"):
        return True, f"Video unavailable ({availability})"

    return False, ""


def extract_youtube_playlist(
    source_name: str,
    config: ScraperConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, Optional[int], int, int, int], None]] = None,
) -> ExtractionResult:
    """
    Extracts metadata entries from a YouTube playlist using yt-dlp.
    Does NOT download media files.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp is required for YouTube extraction. Run 'pip install yt-dlp'.")

    playlist_url = PLAYLIST_URL_MAP.get(source_name)
    if not playlist_url:
        raise ValueError(f"Unknown source name: '{source_name}'. Expected 'watch_later' or 'liked'.")

    ydl_opts: Dict[str, Any] = {
        "skip_download": True,
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    if config.cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (config.cookies_from_browser,)
    elif config.cookies_file.exists():
        ydl_opts["cookiefile"] = str(config.cookies_file)

    if limit and limit > 0:
        ydl_opts["playlistend"] = limit


    valid_entries: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    success_count = 0
    unavailable_count = 0
    failed_count = 0
    total_processed = 0

    checkpoint_file = config.checkpoints_dir / f"{source_name}_checkpoint.json"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if not info:
            raise RuntimeError(f"Could not retrieve playlist info for '{source_name}'. Check cookies and internet connection.")

        raw_entries_generator = info.get("entries")
        playlist_title = info.get("title", source_name.replace("_", " ").title())
        reported_total = info.get("playlist_count") or (limit if limit else None)

        if raw_entries_generator is not None:
            for item in raw_entries_generator:
                total_processed += 1

                if limit and total_processed > limit:
                    break

                unavail, reason = is_entry_unavailable(item)
                if unavail:
                    unavailable_count += 1
                    vid = (item.get("id") if item else None) or "unknown"
                    errors.append({
                        "video_id": vid,
                        "source": source_name,
                        "error": reason,
                        "timestamp": iso_now(),
                    })
                elif item:
                    vid = extract_canonical_video_id(item.get("id"), item.get("url"))
                    if vid:
                        success_count += 1
                        valid_entries.append(item)
                    else:
                        failed_count += 1
                        errors.append({
                            "video_id": item.get("id") or "unknown",
                            "source": source_name,
                            "error": "Could not parse canonical video ID",
                            "timestamp": iso_now(),
                        })
                else:
                    failed_count += 1
                    errors.append({
                        "video_id": "unknown",
                        "source": source_name,
                        "error": "Empty entry",
                        "timestamp": iso_now(),
                    })

                # Progress callback
                if progress_callback:
                    progress_callback(total_processed, reported_total, success_count, unavailable_count, failed_count)

                # Periodic Checkpoint
                if config.save_checkpoints and (total_processed % config.checkpoint_interval == 0):
                    try:
                        temp_cp = checkpoint_file.with_suffix(".tmp")
                        with open(temp_cp, "w", encoding="utf-8") as cp_f:
                            json.dump({
                                "source": source_name,
                                "total_processed": total_processed,
                                "entries_count": len(valid_entries),
                                "entries": valid_entries,
                                "timestamp": iso_now(),
                            }, cp_f)
                        temp_cp.replace(checkpoint_file)
                    except Exception:
                        pass

    # Clean up checkpoint on complete extraction
    if checkpoint_file.exists() and not dry_run:
        try:
            checkpoint_file.unlink()
        except Exception:
            pass

    return ExtractionResult(
        source_name=source_name,
        playlist_title=playlist_title,
        entries=valid_entries,
        errors=errors,
        total_processed=total_processed,
        success_count=success_count,
        unavailable_count=unavailable_count,
        failed_count=failed_count,
    )
