"""
Merge module.
Combines normalized video records from Watch Later, Liked Videos, and custom Playlists
into a unified, deduplicated collection with accurate source tagging, playlist references, and position tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from scraper.normalize import (
    ChannelInfo,
    PlaylistRecord,
    PlaylistReference,
    ThumbnailInfo,
    VideoRecord,
)


@dataclass
class MergeSummary:
    total_watch_later: int
    total_liked: int
    total_custom_playlists: int
    total_playlist_videos: int
    total_unique: int
    overlap_count: int
    duplicates_in_watch_later: int
    duplicates_in_liked: int


def merge_single_record(base: VideoRecord, incoming: VideoRecord) -> VideoRecord:
    """
    Merges metadata from an incoming VideoRecord into an existing base VideoRecord.
    Prefers non-null fields and unions sources, source_positions, and playlist references.
    """
    # Merge sources
    combined_sources = set(base.sources) | set(incoming.sources)

    # Merge source positions
    merged_positions = dict(base.source_positions)
    for src, pos in incoming.source_positions.items():
        if pos is not None:
            if merged_positions.get(src) is None:
                merged_positions[src] = pos

    # Merge playlist references
    existing_pids = {
        (p.id if isinstance(p, PlaylistReference) else p.get("id"))
        for p in base.playlists
    }
    merged_playlists = list(base.playlists)
    for p in incoming.playlists:
        pid = p.id if isinstance(p, PlaylistReference) else p.get("id")
        if pid not in existing_pids:
            existing_pids.add(pid)
            merged_playlists.append(p)

    # Prefer non-empty title
    title = base.title or incoming.title

    # Prefer non-empty channel name and ID
    channel_name = base.channel.name or incoming.channel.name
    channel_id = base.channel.id or incoming.channel.id
    channel = ChannelInfo(name=channel_name, id=channel_id)

    # Prefer non-empty thumbnail URL
    thumbnail_url = base.thumbnail.url or incoming.thumbnail.url
    thumbnail = ThumbnailInfo(url=thumbnail_url)

    # Prefer non-null duration
    duration = base.duration_seconds if base.duration_seconds is not None else incoming.duration_seconds

    # Prefer non-null upload date
    upload_date = base.upload_date or incoming.upload_date

    # Prefer non-empty description
    description = base.description or incoming.description

    return VideoRecord(
        video_id=base.video_id,
        url=base.url,
        title=title,
        channel=channel,
        thumbnail=thumbnail,
        duration_seconds=duration,
        upload_date=upload_date,
        description=description,
        sources=sorted(list(combined_sources)),
        source_positions=merged_positions,
        playlists=merged_playlists,
    )


def merge_sources(
    watch_later_records: List[VideoRecord],
    liked_records: List[VideoRecord],
    custom_playlist_records: Optional[Dict[str, List[VideoRecord]]] = None,
    playlists_info: Optional[List[PlaylistRecord]] = None,
) -> Tuple[List[VideoRecord], List[PlaylistRecord], MergeSummary]:
    """
    Merges Watch Later, Liked, and all custom Playlists into a single deduplicated video list
    and generates updated PlaylistRecords with accurate video_ids arrays.
    """
    merged_map: Dict[str, VideoRecord] = {}
    ordered_ids: List[str] = []

    wl_duplicates = 0
    liked_duplicates = 0
    overlap_count = 0
    total_custom_videos = 0

    # 1. Process Watch Later
    for record in watch_later_records:
        vid = record.video_id
        if vid in merged_map:
            wl_duplicates += 1
            merged_map[vid] = merge_single_record(merged_map[vid], record)
        else:
            merged_map[vid] = record
            ordered_ids.append(vid)

    # 2. Process Liked
    for record in liked_records:
        vid = record.video_id
        if vid in merged_map:
            if "watch_later" in merged_map[vid].sources and "liked" not in merged_map[vid].sources:
                overlap_count += 1
            elif "liked" in merged_map[vid].sources:
                liked_duplicates += 1

            merged_map[vid] = merge_single_record(merged_map[vid], record)
        else:
            merged_map[vid] = record
            ordered_ids.append(vid)

    # 3. Process Custom Playlists
    updated_playlists: List[PlaylistRecord] = []
    custom_playlist_records = custom_playlist_records or {}
    playlists_info_map = {p.playlist_id: p for p in (playlists_info or [])}

    for pid, records in custom_playlist_records.items():
        total_custom_videos += len(records)
        playlist_vids: List[str] = []

        for record in records:
            vid = record.video_id
            playlist_vids.append(vid)

            if vid in merged_map:
                if not any(s.startswith("playlist:") for s in merged_map[vid].sources):
                    overlap_count += 1
                merged_map[vid] = merge_single_record(merged_map[vid], record)
            else:
                merged_map[vid] = record
                ordered_ids.append(vid)

        # Build or update PlaylistRecord
        if pid in playlists_info_map:
            pl_record = playlists_info_map[pid]
            pl_record.video_ids = playlist_vids
            pl_record.video_count = len(playlist_vids)
            updated_playlists.append(pl_record)
        else:
            first_pl_ref = records[0].playlists[0] if records and records[0].playlists else None
            title = first_pl_ref.title if first_pl_ref else f"Playlist {pid}"
            updated_playlists.append(
                PlaylistRecord(
                    playlist_id=pid,
                    title=title,
                    url=f"https://www.youtube.com/playlist?list={pid}",
                    description=None,
                    channel=ChannelInfo(name=None, id=None),
                    video_count=len(playlist_vids),
                    video_ids=playlist_vids,
                )
            )

    final_videos = [merged_map[vid] for vid in ordered_ids]

    summary = MergeSummary(
        total_watch_later=len(watch_later_records),
        total_liked=len(liked_records),
        total_custom_playlists=len(custom_playlist_records),
        total_playlist_videos=total_custom_videos,
        total_unique=len(final_videos),
        overlap_count=overlap_count,
        duplicates_in_watch_later=wl_duplicates,
        duplicates_in_liked=liked_duplicates,
    )

    return final_videos, updated_playlists, summary
