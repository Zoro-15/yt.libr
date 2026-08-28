"""
YouTube extraction module.
Wraps yt-dlp to extract playlist metadata (Watch Later, Liked Videos, User Playlists, and custom Playlists)
without downloading media, with support for batching, limits, progress tracking, resilient error handling, and checkpoints.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from scraper.config import ScraperConfig
from scraper.normalize import (
    extract_canonical_playlist_id,
    extract_canonical_video_id,
)
from scraper.utils import iso_now, print_progress


PLAYLIST_URL_MAP = {
    "watch_later": "https://www.youtube.com/playlist?list=WL",
    "liked": "https://www.youtube.com/playlist?list=LL",
}


@dataclass
class ExtractionResult:
    source_name: str
    playlist_id: str
    playlist_title: str
    playlist_description: Optional[str]
    channel_name: Optional[str]
    channel_id: Optional[str]
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


def get_ydl_options(config: ScraperConfig, limit: Optional[int] = None) -> Dict[str, Any]:
    """Build standard yt-dlp options dictionary."""
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

    return ydl_opts


def discover_user_playlists(
    config: ScraperConfig,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Discovers all playlists created or saved in the authenticated user's YouTube account.
    Queries https://www.youtube.com/feed/playlists.
    Filters out dynamic radio / mix playlists (RD...) that cannot be fetched as static playlists.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp is required. Run 'pip install yt-dlp'.")

    feed_url = "https://www.youtube.com/feed/playlists"
    ydl_opts = get_ydl_options(config, limit=limit)

    discovered_playlists: List[Dict[str, Any]] = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(feed_url, download=False)
            if not info:
                return []

            entries = info.get("entries") or []
            for item in entries:
                if not item:
                    continue
                pid = extract_canonical_playlist_id(item.get("id"), item.get("url"))
                if pid:
                    # Ignore YouTube Mix / Radio streams (RD... or RDEM...) which are not static playlists
                    if pid.startswith("RD"):
                        continue

                    discovered_playlists.append({
                        "id": pid,
                        "title": item.get("title") or f"Playlist {pid}",
                        "url": f"https://www.youtube.com/playlist?list={pid}",
                        "description": item.get("description"),
                        "channel": item.get("channel") or item.get("uploader"),
                        "channel_id": item.get("channel_id") or item.get("uploader_id"),
                        "playlist_count": item.get("playlist_count"),
                    })
    except Exception:
        pass

    return discovered_playlists


def extract_youtube_playlist(
    source_name_or_url: str,
    config: ScraperConfig,
    limit: Optional[int] = None,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, Optional[int], int, int, int], None]] = None,
) -> ExtractionResult:
    """
    Extracts metadata entries from a YouTube playlist using yt-dlp.
    Supports 'watch_later', 'liked', or arbitrary playlist URL/ID (e.g. 'PL...').
    Does NOT download media files.
    Gracefully handles unviewable, private, or mix playlist types.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp is required for YouTube extraction. Run 'pip install yt-dlp'.")

    # Determine playlist URL and ID
    if source_name_or_url == "watch_later":
        playlist_url = PLAYLIST_URL_MAP["watch_later"]
        playlist_id = "WL"
        source_name = "watch_later"
    elif source_name_or_url == "liked":
        playlist_url = PLAYLIST_URL_MAP["liked"]
        playlist_id = "LL"
        source_name = "liked"
    else:
        # Custom playlist URL or ID
        extracted_id = extract_canonical_playlist_id(source_name_or_url, source_name_or_url)
        playlist_id = extracted_id or source_name_or_url
        if source_name_or_url.startswith("http"):
            playlist_url = source_name_or_url
        else:
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        source_name = f"playlist:{playlist_id}"

    # Handle YouTube Mix / Radio IDs (RD...)
    if playlist_id.startswith("RD"):
        return ExtractionResult(
            source_name=source_name,
            playlist_id=playlist_id,
            playlist_title=f"YouTube Mix ({playlist_id})",
            playlist_description="Dynamic auto-generated YouTube Mix (unviewable as static playlist)",
            channel_name=None,
            channel_id=None,
            entries=[],
            errors=[{
                "video_id": playlist_id,
                "source": source_name,
                "error": "Dynamic YouTube Mix / Radio (RD...) is auto-generated and unviewable as a static playlist.",
                "timestamp": iso_now(),
            }],
            total_processed=0,
            success_count=0,
            unavailable_count=0,
            failed_count=1,
        )

    ydl_opts = get_ydl_options(config, limit=limit)

    valid_entries: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    success_count = 0
    unavailable_count = 0
    failed_count = 0
    total_processed = 0

    checkpoint_file = config.checkpoints_dir / f"{playlist_id}_checkpoint.json"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            if not info:
                return ExtractionResult(
                    source_name=source_name,
                    playlist_id=playlist_id,
                    playlist_title=source_name.replace("_", " ").title(),
                    playlist_description=None,
                    channel_name=None,
                    channel_id=None,
                    entries=[],
                    errors=[{
                        "video_id": playlist_id,
                        "source": source_name,
                        "error": "YouTube returned empty response for playlist.",
                        "timestamp": iso_now(),
                    }],
                    total_processed=0,
                    success_count=0,
                    unavailable_count=0,
                    failed_count=1,
                )

            raw_entries_generator = info.get("entries")
            playlist_title = info.get("title") or (source_name.replace("_", " ").title())
            playlist_description = info.get("description") or None
            channel_name = info.get("channel") or info.get("uploader") or None
            channel_id = info.get("channel_id") or info.get("uploader_id") or None
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
                                    "playlist_id": playlist_id,
                                    "total_processed": total_processed,
                                    "entries_count": len(valid_entries),
                                    "entries": valid_entries,
                                    "timestamp": iso_now(),
                                }, cp_f)
                            temp_cp.replace(checkpoint_file)
                        except Exception:
                            pass

    except Exception as e:
        error_msg = str(e)
        errors.append({
            "video_id": playlist_id,
            "source": source_name,
            "error": error_msg,
            "timestamp": iso_now(),
        })
        failed_count += 1
        playlist_title = source_name.replace("_", " ").title()
        playlist_description = None
        channel_name = None
        channel_id = None

    # Clean up checkpoint on complete extraction
    if checkpoint_file.exists() and not dry_run:
        try:
            checkpoint_file.unlink()
        except Exception:
            pass

    return ExtractionResult(
        source_name=source_name,
        playlist_id=playlist_id,
        playlist_title=playlist_title,
        playlist_description=playlist_description,
        channel_name=channel_name,
        channel_id=channel_id,
        entries=valid_entries,
        errors=errors,
        total_processed=total_processed,
        success_count=success_count,
        unavailable_count=unavailable_count,
        failed_count=failed_count,
    )
