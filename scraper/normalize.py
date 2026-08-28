"""
Normalization module.
Converts raw yt-dlp extracted entries into canonical VideoRecord structures.
Strictly extracts YouTube metadata only and rejects personal database fields.
"""

from dataclasses import dataclass, asdict
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse


YOUTUBE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@dataclass
class ChannelInfo:
    name: Optional[str]
    id: Optional[str]

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {"name": self.name, "id": self.id}


@dataclass
class ThumbnailInfo:
    url: Optional[str]

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {"url": self.url}


@dataclass
class VideoRecord:
    video_id: str
    url: str
    title: Optional[str]
    channel: ChannelInfo
    thumbnail: ThumbnailInfo
    duration_seconds: Optional[int]
    upload_date: Optional[str]
    description: Optional[str]
    sources: List[str]
    source_positions: Dict[str, Optional[int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "url": self.url,
            "title": self.title,
            "channel": self.channel.to_dict(),
            "thumbnail": self.thumbnail.to_dict(),
            "duration_seconds": self.duration_seconds,
            "upload_date": self.upload_date,
            "description": self.description,
            "sources": sorted(list(set(self.sources))),
            "source_positions": self.source_positions,
        }


def extract_canonical_video_id(raw_id: Optional[str], raw_url: Optional[str] = None) -> Optional[str]:
    """
    Extracts and validates a clean 11-character YouTube video ID.
    Falls back to parsing the video URL if id is missing.
    """
    if raw_id and isinstance(raw_id, str):
        cleaned_id = raw_id.strip()
        if YOUTUBE_ID_REGEX.match(cleaned_id):
            return cleaned_id
        if len(cleaned_id) >= 11:
            # Check if there's an 11-char pattern inside
            match = YOUTUBE_ID_REGEX.search(cleaned_id)
            if match:
                return match.group(0)

    if raw_url and isinstance(raw_url, str):
        parsed = urlparse(raw_url.strip())
        if parsed.hostname in ("youtu.be", "www.youtu.be"):
            vid = parsed.path.lstrip("/").split("?")[0].split("&")[0]
            if YOUTUBE_ID_REGEX.match(vid):
                return vid
        if parsed.query:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                vid = qs["v"][0]
                if YOUTUBE_ID_REGEX.match(vid):
                    return vid
        if "/shorts/" in parsed.path:
            vid = parsed.path.split("/shorts/")[1].split("/")[0].split("?")[0]
            if YOUTUBE_ID_REGEX.match(vid):
                return vid

    return None


def format_upload_date(raw_date: Optional[Union[str, int]]) -> Optional[str]:
    """
    Formats upload date to ISO format YYYY-MM-DD.
    Accepts 'YYYYMMDD', 'YYYY-MM-DD', or integer timestamps.
    """
    if not raw_date:
        return None

    str_date = str(raw_date).strip()
    if len(str_date) == 8 and str_date.isdigit():
        return f"{str_date[0:4]}-{str_date[4:6]}-{str_date[6:8]}"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", str_date):
        return str_date

    return None


def pick_best_thumbnail_url(entry: Dict[str, Any]) -> Optional[str]:
    """
    Picks the best thumbnail URL from yt-dlp entry data.
    """
    # Direct thumbnail field
    thumb = entry.get("thumbnail")
    if thumb and isinstance(thumb, str) and thumb.startswith("http"):
        return thumb.strip()

    # List of thumbnails
    thumbs = entry.get("thumbnails")
    if isinstance(thumbs, list) and thumbs:
        valid_thumbs = [
            t for t in thumbs
            if isinstance(t, dict) and t.get("url") and isinstance(t["url"], str) and t["url"].startswith("http")
        ]
        if valid_thumbs:
            # Sort by width / preference if available
            valid_thumbs.sort(key=lambda t: (t.get("preference", 0) or 0, t.get("width", 0) or 0))
            return valid_thumbs[-1]["url"].strip()

    # If we have video_id, construct maxres / hqdefault fallback
    vid = entry.get("id")
    if vid and isinstance(vid, str) and YOUTUBE_ID_REGEX.match(vid.strip()):
        return f"https://i.ytimg.com/vi/{vid.strip()}/hqdefault.jpg"

    return None


def normalize_entry(
    entry: Dict[str, Any],
    source_name: str,
    position: Optional[int] = None,
) -> Optional[VideoRecord]:
    """
    Normalizes a single raw yt-dlp entry into a clean VideoRecord.
    Returns None if entry is completely invalid or has no identifiable video_id.
    """
    if not isinstance(entry, dict):
        return None

    raw_id = entry.get("id") or entry.get("video_id")
    raw_url = entry.get("url") or entry.get("webpage_url")
    
    video_id = extract_canonical_video_id(raw_id, raw_url)
    if not video_id:
        return None

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    # Title extraction
    title = entry.get("title")
    if isinstance(title, str):
        title = title.strip()
        if not title:
            title = None
    else:
        title = None

    # Channel extraction
    channel_name = (
        entry.get("channel")
        or entry.get("uploader")
        or entry.get("channel_name")
        or entry.get("uploader_name")
    )
    if isinstance(channel_name, str):
        channel_name = channel_name.strip() or None
    else:
        channel_name = None

    channel_id = (
        entry.get("channel_id")
        or entry.get("uploader_id")
        or entry.get("channel_url")
    )
    if isinstance(channel_id, str):
        channel_id = channel_id.strip() or None
    else:
        channel_id = None

    channel = ChannelInfo(name=channel_name, id=channel_id)

    # Thumbnail
    thumb_url = pick_best_thumbnail_url(entry)
    thumbnail = ThumbnailInfo(url=thumb_url)

    # Duration in integer seconds
    duration = entry.get("duration")
    duration_seconds: Optional[int] = None
    if duration is not None:
        try:
            dur_float = float(duration)
            if dur_float >= 0:
                duration_seconds = int(dur_float)
        except (ValueError, TypeError):
            duration_seconds = None

    # Upload date
    upload_date = format_upload_date(entry.get("upload_date") or entry.get("release_date"))

    # Description
    description = entry.get("description")
    if isinstance(description, str):
        description = description.strip() or None
    else:
        description = None

    # Source and position tracking
    sources = [source_name] if source_name else []
    source_positions = {
        "watch_later": position if source_name == "watch_later" else None,
        "liked": position if source_name == "liked" else None,
    }

    return VideoRecord(
        video_id=video_id,
        url=canonical_url,
        title=title,
        channel=channel,
        thumbnail=thumbnail,
        duration_seconds=duration_seconds,
        upload_date=upload_date,
        description=description,
        sources=sources,
        source_positions=source_positions,
    )


def normalize_raw_entries(
    raw_entries: List[Dict[str, Any]],
    source_name: str,
) -> List[VideoRecord]:
    """
    Normalizes a list of raw entries from a specific source.
    Preserves 1-indexed position in source_positions.
    """
    normalized_list: List[VideoRecord] = []
    position = 1

    for entry in raw_entries:
        if not entry:
            continue
        record = normalize_entry(entry, source_name=source_name, position=position)
        if record:
            normalized_list.append(record)
            position += 1

    return normalized_list
