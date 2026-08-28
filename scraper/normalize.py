"""
Normalization module.
Converts raw yt-dlp extracted entries and playlists into canonical structures:
- VideoRecord (YouTube metadata only, with source tagging and playlist references)
- PlaylistRecord (YouTube playlist metadata and ordered video_id references)
Strictly extracts YouTube metadata only and rejects personal database fields.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse


YOUTUBE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")
PLAYLIST_ID_REGEX = re.compile(r"^(PL|FL|UU|RD|LL|WL|OLAK5uy_)[a-zA-Z0-9_-]+$|^[a-zA-Z0-9_-]{12,}$")


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
class PlaylistReference:
    id: str
    title: str
    position: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "position": self.position,
        }


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
    playlists: List[PlaylistReference] = field(default_factory=list)

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
            "playlists": [p.to_dict() if isinstance(p, PlaylistReference) else p for p in self.playlists],
        }


@dataclass
class PlaylistRecord:
    playlist_id: str
    title: str
    url: str
    description: Optional[str]
    channel: ChannelInfo
    video_count: int
    video_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "playlist_id": self.playlist_id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "channel": self.channel.to_dict(),
            "video_count": self.video_count,
            "video_ids": self.video_ids,
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


def extract_canonical_playlist_id(raw_id: Optional[str], raw_url: Optional[str] = None) -> Optional[str]:
    """
    Extracts canonical playlist ID (e.g. PL..., WL, LL) from string ID or playlist URL.
    """
    if raw_id and isinstance(raw_id, str):
        cid = raw_id.strip()
        if cid in ("WL", "LL") or PLAYLIST_ID_REGEX.match(cid):
            return cid

    if raw_url and isinstance(raw_url, str):
        parsed = urlparse(raw_url.strip())
        if parsed.query:
            qs = parse_qs(parsed.query)
            if "list" in qs and qs["list"]:
                pid = qs["list"][0]
                if pid in ("WL", "LL") or PLAYLIST_ID_REGEX.match(pid):
                    return pid
        if "/playlist/" in parsed.path:
            parts = parsed.path.split("/playlist/")[1].split("/")
            if parts and parts[0]:
                return parts[0]

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
    thumb = entry.get("thumbnail")
    if thumb and isinstance(thumb, str) and thumb.startswith("http"):
        return thumb.strip()

    thumbs = entry.get("thumbnails")
    if isinstance(thumbs, list) and thumbs:
        valid_thumbs = [
            t for t in thumbs
            if isinstance(t, dict) and t.get("url") and isinstance(t["url"], str) and t["url"].startswith("http")
        ]
        if valid_thumbs:
            valid_thumbs.sort(key=lambda t: (t.get("preference", 0) or 0, t.get("width", 0) or 0))
            return valid_thumbs[-1]["url"].strip()

    vid = entry.get("id")
    if vid and isinstance(vid, str) and YOUTUBE_ID_REGEX.match(vid.strip()):
        return f"https://i.ytimg.com/vi/{vid.strip()}/hqdefault.jpg"

    return None


def normalize_entry(
    entry: Dict[str, Any],
    source_name: str,
    position: Optional[int] = None,
    playlist_id: Optional[str] = None,
    playlist_title: Optional[str] = None,
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
    source_positions: Dict[str, Optional[int]] = {
        "watch_later": position if source_name == "watch_later" else None,
        "liked": position if source_name == "liked" else None,
    }

    playlists: List[PlaylistReference] = []
    if playlist_id:
        source_key = f"playlist:{playlist_id}"
        if source_key not in sources:
            sources.append(source_key)
        source_positions[playlist_id] = position
        playlists.append(
            PlaylistReference(
                id=playlist_id,
                title=playlist_title or f"Playlist {playlist_id}",
                position=position,
            )
        )

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
        playlists=playlists,
    )


def normalize_raw_entries(
    raw_entries: List[Dict[str, Any]],
    source_name: str,
    playlist_id: Optional[str] = None,
    playlist_title: Optional[str] = None,
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
        record = normalize_entry(
            entry,
            source_name=source_name,
            position=position,
            playlist_id=playlist_id,
            playlist_title=playlist_title,
        )
        if record:
            normalized_list.append(record)
            position += 1

    return normalized_list


def normalize_playlist_info(
    raw_info: Dict[str, Any],
    video_ids: Optional[List[str]] = None,
) -> Optional[PlaylistRecord]:
    """
    Normalizes raw playlist metadata into a PlaylistRecord.
    """
    if not isinstance(raw_info, dict):
        return None

    raw_id = raw_info.get("id") or raw_info.get("playlist_id")
    raw_url = raw_info.get("url") or raw_info.get("webpage_url")
    pid = extract_canonical_playlist_id(raw_id, raw_url)
    if not pid:
        return None

    title = (raw_info.get("title") or f"Playlist {pid}").strip()
    url = f"https://www.youtube.com/playlist?list={pid}"
    desc = raw_info.get("description") or None

    ch_name = (
        raw_info.get("channel")
        or raw_info.get("uploader")
        or raw_info.get("channel_name")
        or raw_info.get("uploader_name")
    )
    ch_id = (
        raw_info.get("channel_id")
        or raw_info.get("uploader_id")
    )
    channel = ChannelInfo(name=ch_name, id=ch_id)

    vids = video_ids or []
    count = raw_info.get("playlist_count") or len(vids)

    return PlaylistRecord(
        playlist_id=pid,
        title=title,
        url=url,
        description=desc,
        channel=channel,
        video_count=count,
        video_ids=vids,
    )
