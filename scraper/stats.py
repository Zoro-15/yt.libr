"""
Stats module.
Computes comprehensive metrics and summary statistics for the video library.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scraper.utils import SEP_LINE, bold, green, yellow, cyan, dim


@dataclass
class LibraryStats:
    total_unique: int
    watch_later_total: int
    liked_total: int
    both_sources_count: int
    watch_later_only: int
    liked_only: int
    missing_thumbnails: int
    missing_duration: int
    missing_channel: int
    missing_upload_date: int
    total_duration_seconds: int

    def format_total_duration(self) -> str:
        hours = self.total_duration_seconds // 3600
        minutes = (self.total_duration_seconds % 3600) // 60
        seconds = self.total_duration_seconds % 60
        if hours > 0:
            return f"{hours:,}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

    def print_report(self) -> None:
        print(bold("\n=================================================="))
        print(bold(" YouTube Library Statistics"))
        print(bold("=================================================="))
        print(f"Total Unique Videos:      {cyan(f'{self.total_unique:,}')}")
        print(f"Watch Later Videos:       {cyan(f'{self.watch_later_total:,}')}")
        print(f"Liked Videos:             {cyan(f'{self.liked_total:,}')}")
        print(SEP_LINE)
        print(f"Appearing in Both:        {green(f'{self.both_sources_count:,}')}")
        print(f"Watch Later Only:         {self.watch_later_only:,}")
        print(f"Liked Only:               {self.liked_only:,}")
        print(SEP_LINE)

        print(f"Total Known Playtime:     {cyan(self.format_total_duration())}")
        print(f"Missing Thumbnails:       {yellow(f'{self.missing_thumbnails:,}') if self.missing_thumbnails else green('0')}")
        print(f"Missing Duration:         {yellow(f'{self.missing_duration:,}') if self.missing_duration else green('0')}")
        print(f"Missing Channel Name:     {yellow(f'{self.missing_channel:,}') if self.missing_channel else green('0')}")
        print(f"Missing Upload Date:      {dim(f'{self.missing_upload_date:,}')}")
        print(bold("==================================================\n"))


def compute_library_stats(videos_json_path: Path) -> Optional[LibraryStats]:
    """
    Reads videos.json and calculates all metrics.
    """
    if not videos_json_path.exists():
        return None

    try:
        with open(videos_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    videos = data.get("videos", []) if isinstance(data, dict) else []
    if not videos:
        return LibraryStats(
            total_unique=0,
            watch_later_total=0,
            liked_total=0,
            both_sources_count=0,
            watch_later_only=0,
            liked_only=0,
            missing_thumbnails=0,
            missing_duration=0,
            missing_channel=0,
            missing_upload_date=0,
            total_duration_seconds=0,
        )

    wl_count = 0
    liked_count = 0
    both_count = 0
    wl_only = 0
    liked_only = 0
    missing_thumb = 0
    missing_dur = 0
    missing_chan = 0
    missing_date = 0
    total_dur = 0

    for v in videos:
        sources = v.get("sources", [])
        is_wl = "watch_later" in sources
        is_liked = "liked" in sources

        if is_wl:
            wl_count += 1
        if is_liked:
            liked_count += 1

        if is_wl and is_liked:
            both_count += 1
        elif is_wl:
            wl_only += 1
        elif is_liked:
            liked_only += 1

        # Check metadata completeness
        thumb = v.get("thumbnail", {})
        if not thumb or not thumb.get("url"):
            missing_thumb += 1

        dur = v.get("duration_seconds")
        if dur is None:
            missing_dur += 1
        else:
            total_dur += dur

        channel = v.get("channel", {})
        if not channel or not channel.get("name"):
            missing_chan += 1

        if not v.get("upload_date"):
            missing_date += 1

    return LibraryStats(
        total_unique=len(videos),
        watch_later_total=wl_count,
        liked_total=liked_count,
        both_sources_count=both_count,
        watch_later_only=wl_only,
        liked_only=liked_only,
        missing_thumbnails=missing_thumb,
        missing_duration=missing_dur,
        missing_channel=missing_chan,
        missing_upload_date=missing_date,
        total_duration_seconds=total_dur,
    )
