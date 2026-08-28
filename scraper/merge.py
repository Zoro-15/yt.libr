"""
Merge module.
Combines normalized video records from Watch Later and Liked Videos sources
into a unified, deduplicated collection with accurate source tagging and position tracking.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from scraper.normalize import ChannelInfo, ThumbnailInfo, VideoRecord


@dataclass
class MergeSummary:
    total_watch_later: int
    total_liked: int
    total_unique: int
    overlap_count: int
    duplicates_in_watch_later: int
    duplicates_in_liked: int


def merge_single_record(base: VideoRecord, incoming: VideoRecord) -> VideoRecord:
    """
    Merges metadata from an incoming VideoRecord into an existing base VideoRecord.
    Prefers non-null fields and unions sources and source_positions.
    """
    # Merge sources
    combined_sources = set(base.sources) | set(incoming.sources)

    # Merge source positions
    merged_positions = dict(base.source_positions)
    for src, pos in incoming.source_positions.items():
        if pos is not None:
            if merged_positions.get(src) is None:
                merged_positions[src] = pos

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
    )


def merge_sources(
    watch_later_records: List[VideoRecord],
    liked_records: List[VideoRecord],
) -> Tuple[List[VideoRecord], MergeSummary]:
    """
    Merges Watch Later and Liked video lists into a single deduplicated list.
    Preserves Watch Later order, appending Liked-only videos afterwards.
    """
    merged_map: Dict[str, VideoRecord] = {}
    ordered_ids: List[str] = []

    wl_duplicates = 0
    liked_duplicates = 0
    overlap_count = 0

    # Process Watch Later
    for record in watch_later_records:
        vid = record.video_id
        if vid in merged_map:
            wl_duplicates += 1
            merged_map[vid] = merge_single_record(merged_map[vid], record)
        else:
            merged_map[vid] = record
            ordered_ids.append(vid)

    # Process Liked
    for record in liked_records:
        vid = record.video_id
        if vid in merged_map:
            # Check if this is an overlap between sources or a duplicate within liked
            if "watch_later" in merged_map[vid].sources and "liked" not in merged_map[vid].sources:
                overlap_count += 1
            elif "liked" in merged_map[vid].sources:
                liked_duplicates += 1

            merged_map[vid] = merge_single_record(merged_map[vid], record)
        else:
            merged_map[vid] = record
            ordered_ids.append(vid)

    final_records = [merged_map[vid] for vid in ordered_ids]

    summary = MergeSummary(
        total_watch_later=len(watch_later_records),
        total_liked=len(liked_records),
        total_unique=len(final_records),
        overlap_count=overlap_count,
        duplicates_in_watch_later=wl_duplicates,
        duplicates_in_liked=liked_duplicates,
    )

    return final_records, summary
