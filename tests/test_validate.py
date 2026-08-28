"""
Unit tests for schema and integrity validation.
"""

import json
from pathlib import Path
import tempfile
import unittest

from scraper.validate import validate_videos_json


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "videos.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_json(self, data):
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_valid_json_passes(self):
        valid_data = {
            "schema_version": 1,
            "generated_at": "2026-08-28T09:30:00Z",
            "source": "youtube",
            "total_videos": 1,
            "videos": [
                {
                    "video_id": "dQw4w9WgXcQ",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "title": "Never Gonna Give You Up",
                    "channel": {"name": "Rick Astley", "id": "UC123"},
                    "thumbnail": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"},
                    "duration_seconds": 212,
                    "upload_date": "2009-10-25",
                    "description": "Official video",
                    "sources": ["watch_later", "liked"],
                    "source_positions": {"watch_later": 1, "liked": 5},
                }
            ],
        }
        self.write_json(valid_data)
        report = validate_videos_json(self.test_file)
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.errors), 0)

    def test_missing_schema_version_fails(self):
        data = {
            "generated_at": "2026-08-28T09:30:00Z",
            "source": "youtube",
            "videos": [],
        }
        self.write_json(data)
        report = validate_videos_json(self.test_file)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("schema_version" in e for e in report.errors))

    def test_duplicate_video_id_fails(self):
        data = {
            "schema_version": 1,
            "generated_at": "2026-08-28T09:30:00Z",
            "source": "youtube",
            "total_videos": 2,
            "videos": [
                {
                    "video_id": "duplicate_id",
                    "url": "https://www.youtube.com/watch?v=duplicate_id",
                    "channel": {},
                    "thumbnail": {},
                    "sources": ["watch_later"],
                },
                {
                    "video_id": "duplicate_id",
                    "url": "https://www.youtube.com/watch?v=duplicate_id",
                    "channel": {},
                    "thumbnail": {},
                    "sources": ["liked"],
                },
            ],
        }
        self.write_json(data)
        report = validate_videos_json(self.test_file)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("Duplicate video_id" in e for e in report.errors))

    def test_forbidden_personal_fields_fail(self):
        data = {
            "schema_version": 1,
            "generated_at": "2026-08-28T09:30:00Z",
            "source": "youtube",
            "total_videos": 1,
            "videos": [
                {
                    "video_id": "vid12345678",
                    "url": "https://www.youtube.com/watch?v=vid12345678",
                    "channel": {},
                    "thumbnail": {},
                    "sources": ["watch_later"],
                    # Forbidden personal tags
                    "category": "Tech",
                    "tags": ["python", "termux"],
                }
            ],
        }
        self.write_json(data)
        report = validate_videos_json(self.test_file)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("forbidden personal metadata" in e for e in report.errors))


if __name__ == "__main__":
    unittest.main()
