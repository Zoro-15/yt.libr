"""
Output module.
Handles atomic file writes, deterministic formatting, and versioned schema serialization
for raw data, processed videos.json, and machine-readable error logs.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from scraper.normalize import VideoRecord
from scraper.utils import iso_now


def atomic_write_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """
    Atomically writes JSON data to a file by writing to a temporary file
    and renaming it. Prevents file corruption if interrupted.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")
        
        # Replace atomically
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise IOError(f"Failed to write JSON atomically to {file_path}: {e}")


def save_raw_extraction(
    output_path: Path,
    source_name: str,
    raw_entries: List[Dict[str, Any]],
    playlist_title: Optional[str] = None,
) -> None:
    """
    Saves raw extracted yt-dlp entries to data/raw/<source>.json.
    """
    payload = {
        "source": source_name,
        "playlist_title": playlist_title or source_name.replace("_", " ").title(),
        "extracted_at": iso_now(),
        "total_extracted": len(raw_entries),
        "entries": raw_entries,
    }
    atomic_write_json(output_path, payload)


def load_raw_extraction(file_path: Path) -> List[Dict[str, Any]]:
    """
    Loads raw entries from a raw extraction JSON file.
    Supports both wrapped format (with 'entries' key) and direct list format.
    """
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "entries" in data:
        return data.get("entries", [])
    elif isinstance(data, list):
        return data

    return []


def save_processed_videos(
    output_path: Path,
    records: List[VideoRecord],
    schema_version: int = 1,
) -> None:
    """
    Saves the final deduplicated and merged video library to data/processed/videos.json.
    """
    video_dicts = [r.to_dict() for r in records]
    payload = {
        "schema_version": schema_version,
        "generated_at": iso_now(),
        "source": "youtube",
        "total_videos": len(video_dicts),
        "videos": video_dicts,
    }
    atomic_write_json(output_path, payload)


def save_error_log(
    log_path: Path,
    errors: List[Dict[str, Any]],
) -> None:
    """
    Appends/saves machine-readable extraction error reports to data/logs/errors.json.
    """
    existing_errors: List[Dict[str, Any]] = []
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                existing_errors = json.load(f)
                if not isinstance(existing_errors, list):
                    existing_errors = []
        except Exception:
            existing_errors = []

    combined_errors = existing_errors + errors
    atomic_write_json(log_path, combined_errors)
