"""
Deduplication module.
Deduplicates video records strictly by their canonical YouTube video_id.
"""

from typing import Dict, List, Set, Tuple
from scraper.normalize import VideoRecord


def deduplicate_records(records: List[VideoRecord]) -> Tuple[List[VideoRecord], int]:
    """
    Deduplicates a list of VideoRecord instances based purely on video_id.
    Maintains insertion order.
    Returns:
        (deduplicated_records_list, duplicate_count)
    """
    seen_ids: Set[str] = set()
    unique_records: List[VideoRecord] = []
    duplicate_count = 0

    for record in records:
        vid = record.video_id
        if vid in seen_ids:
            duplicate_count += 1
            # Merge sources and positions into existing record if seen
            existing = next(r for r in unique_records if r.video_id == vid)
            for src in record.sources:
                if src not in existing.sources:
                    existing.sources.append(src)
            for src, pos in record.source_positions.items():
                if pos is not None and existing.source_positions.get(src) is None:
                    existing.source_positions[src] = pos
        else:
            seen_ids.add(vid)
            unique_records.append(record)

    return unique_records, duplicate_count
