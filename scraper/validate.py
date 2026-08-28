"""
Validation module.
Performs thorough schema, uniqueness, and integrity validation on videos.json and playlists.json.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from scraper.normalize import YOUTUBE_ID_REGEX


FORBIDDEN_PERSONAL_FIELDS = {
    "category",
    "tags",
    "watched",
    "backlog",
    "favourite",
    "favorite",
    "notes",
    "collections",
    "classification_status",
}

VALID_BASE_SOURCES = {"watch_later", "liked"}


@dataclass
class ValidationReport:
    is_valid: bool
    total_videos: int
    total_playlists: int
    schema_version: Optional[int]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def print_summary(self) -> None:
        from scraper.utils import bold, green, red, yellow, cyan

        print(bold("\n--- YouTube Library Scraper — Validation Report ---"))
        print(f"Total Videos Checked:    {cyan(str(self.total_videos))}")
        print(f"Total Playlists Checked: {cyan(str(self.total_playlists))}")
        print(f"Schema Version:          {cyan(str(self.schema_version))}")
        print(f"Status:                  {green('PASSED') if self.is_valid else red('FAILED')}")

        if self.errors:
            print(red(f"\nErrors ({len(self.errors)}):"))
            for err in self.errors[:20]:
                print(f"  ✗ {err}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more errors.")

        if self.warnings:
            print(yellow(f"\nWarnings ({len(self.warnings)}):"))
            for warn in self.warnings[:20]:
                print(f"  ⚠ {warn}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more warnings.")

        if self.is_valid and not self.warnings:
            print(green("\nAll checks passed cleanly. Output is fully compliant and ready for import!"))


def validate_videos_json(file_path: Path, playlists_path: Optional[Path] = None) -> ValidationReport:
    """
    Validates a processed videos.json (and optional playlists.json) against schema requirements.
    """
    if not file_path.exists():
        return ValidationReport(
            is_valid=False,
            total_videos=0,
            total_playlists=0,
            schema_version=None,
            errors=[f"File not found: {file_path}"],
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return ValidationReport(
            is_valid=False,
            total_videos=0,
            total_playlists=0,
            schema_version=None,
            errors=[f"Failed to parse JSON: {e}"],
        )

    if not isinstance(data, dict):
        return ValidationReport(
            is_valid=False,
            total_videos=0,
            total_playlists=0,
            schema_version=None,
            errors=["Root element must be a JSON Object."],
        )

    errors: List[str] = []
    warnings: List[str] = []

    # Check root fields
    schema_version = data.get("schema_version")
    if schema_version is None or not isinstance(schema_version, int):
        errors.append("Missing or non-integer 'schema_version' in root object.")

    if not data.get("generated_at") or not isinstance(data.get("generated_at"), str):
        errors.append("Missing or invalid 'generated_at' timestamp.")

    if data.get("source") != "youtube":
        warnings.append(f"Unexpected source value: {data.get('source')} (expected 'youtube').")

    videos = data.get("videos")
    if not isinstance(videos, list):
        errors.append("Missing or invalid 'videos' array in root object.")
        return ValidationReport(
            is_valid=False,
            total_videos=0,
            total_playlists=0,
            schema_version=schema_version,
            errors=errors,
            warnings=warnings,
        )

    total_reported = data.get("total_videos")
    if total_reported != len(videos):
        warnings.append(f"Header 'total_videos' ({total_reported}) does not match array length ({len(videos)}).")

    seen_ids: Set[str] = set()

    for idx, video in enumerate(videos):
        ref = f"Video #{idx + 1}"
        if not isinstance(video, dict):
            errors.append(f"{ref}: Record is not an object.")
            continue

        vid = video.get("video_id")
        if not vid or not isinstance(vid, str):
            errors.append(f"{ref}: Missing or invalid 'video_id'.")
            continue

        ref = f"Video '{vid}' (#{idx + 1})"

        # Duplicate ID check
        if vid in seen_ids:
            errors.append(f"{ref}: Duplicate video_id detected! ID must be globally unique.")
        else:
            seen_ids.add(vid)

        # URL format check
        url = video.get("url")
        if not url or not isinstance(url, str) or not url.startswith("https://www.youtube.com/watch?v="):
            errors.append(f"{ref}: Invalid canonical URL format '{url}'.")

        # Personal metadata boundary check
        forbidden_present = set(video.keys()) & FORBIDDEN_PERSONAL_FIELDS
        if forbidden_present:
            errors.append(f"{ref}: Contains forbidden personal metadata keys: {', '.join(forbidden_present)}.")

        # Sources check
        sources = video.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{ref}: 'sources' must be a non-empty list.")
        else:
            for s in sources:
                if s not in VALID_BASE_SOURCES and not s.startswith("playlist:"):
                    errors.append(f"{ref}: Invalid source name '{s}'.")

        # Channel check
        channel = video.get("channel")
        if not isinstance(channel, dict):
            errors.append(f"{ref}: 'channel' must be an object with 'name' and 'id'.")
        elif not channel.get("name"):
            warnings.append(f"{ref}: Channel name is missing/null.")

        # Thumbnail check
        thumbnail = video.get("thumbnail")
        if not isinstance(thumbnail, dict):
            errors.append(f"{ref}: 'thumbnail' must be an object with 'url'.")
        elif not thumbnail.get("url"):
            warnings.append(f"{ref}: Thumbnail URL is null.")

        # Duration check
        duration = video.get("duration_seconds")
        if duration is not None and (not isinstance(duration, int) or duration < 0):
            errors.append(f"{ref}: 'duration_seconds' must be null or a positive integer.")

        # Upload date check
        upload_date = video.get("upload_date")
        if upload_date is not None:
            if not isinstance(upload_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", upload_date):
                warnings.append(f"{ref}: 'upload_date' '{upload_date}' is not in YYYY-MM-DD format.")

        # Playlists list check
        pl_refs = video.get("playlists")
        if pl_refs is not None:
            if not isinstance(pl_refs, list):
                errors.append(f"{ref}: 'playlists' must be a list of playlist reference objects.")
            else:
                for pl in pl_refs:
                    if not isinstance(pl, dict) or not pl.get("id"):
                        errors.append(f"{ref}: Malformed playlist reference in 'playlists' array.")

    # Validate playlists.json if present
    total_playlists = 0
    if playlists_path and playlists_path.exists():
        try:
            with open(playlists_path, "r", encoding="utf-8") as f:
                pl_data = json.load(f)
            
            if isinstance(pl_data, dict):
                pls = pl_data.get("playlists", [])
                total_playlists = len(pls)
                seen_pids: Set[str] = set()

                for pidx, pl in enumerate(pls):
                    pref = f"Playlist #{pidx + 1}"
                    if not isinstance(pl, dict):
                        errors.append(f"{pref}: Record is not an object.")
                        continue
                    
                    pid = pl.get("playlist_id")
                    if not pid or not isinstance(pid, str):
                        errors.append(f"{pref}: Missing or invalid 'playlist_id'.")
                        continue

                    if pid in seen_pids:
                        errors.append(f"Playlist '{pid}': Duplicate playlist_id.")
                    seen_pids.add(pid)

                    # Check video_ids
                    vids = pl.get("video_ids", [])
                    if not isinstance(vids, list):
                        errors.append(f"Playlist '{pid}': 'video_ids' must be a list.")
        except Exception as e:
            errors.append(f"Failed to validate playlists.json: {e}")

    is_valid = len(errors) == 0

    return ValidationReport(
        is_valid=is_valid,
        total_videos=len(videos),
        total_playlists=total_playlists,
        schema_version=schema_version,
        errors=errors,
        warnings=warnings,
    )
