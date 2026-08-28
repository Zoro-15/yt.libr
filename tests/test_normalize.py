"""
Unit tests for metadata normalization.
"""

import unittest
from scraper.normalize import (
    extract_canonical_video_id,
    format_upload_date,
    normalize_entry,
    normalize_raw_entries,
    pick_best_thumbnail_url,
)


class TestNormalize(unittest.TestCase):

    def test_extract_canonical_video_id(self):
        # 11-char direct ID
        self.assertEqual(extract_canonical_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        
        # Standard YouTube watch URL
        self.assertEqual(
            extract_canonical_video_id(None, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

        # youtu.be short URL
        self.assertEqual(
            extract_canonical_video_id(None, "https://youtu.be/dQw4w9WgXcQ?t=10"),
            "dQw4w9WgXcQ",
        )

        # YouTube Shorts URL
        self.assertEqual(
            extract_canonical_video_id(None, "https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

        # Invalid / missing
        self.assertIsNone(extract_canonical_video_id(None, None))
        self.assertIsNone(extract_canonical_video_id("invalid", "https://google.com"))

    def test_format_upload_date(self):
        self.assertEqual(format_upload_date("20250412"), "2025-04-12")
        self.assertEqual(format_upload_date("2025-04-12"), "2025-04-12")
        self.assertIsNone(format_upload_date(None))
        self.assertIsNone(format_upload_date(""))
        self.assertIsNone(format_upload_date("invalid_date"))

    def test_pick_best_thumbnail_url(self):
        entry_with_list = {
            "id": "dQw4w9WgXcQ",
            "thumbnails": [
                {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg", "width": 120, "preference": 1},
                {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg", "width": 480, "preference": 2},
                {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg", "width": 1280, "preference": 3},
            ]
        }
        self.assertEqual(
            pick_best_thumbnail_url(entry_with_list),
            "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        )

    def test_normalize_complete_entry(self):
        raw = {
            "id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "uploader": "Rick Astley",
            "uploader_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            "duration": 212,
            "upload_date": "20091025",
            "description": "The official video for Never Gonna Give You Up.",
        }

        record = normalize_entry(raw, source_name="watch_later", position=5)
        self.assertIsNotNone(record)
        self.assertEqual(record.video_id, "dQw4w9WgXcQ")
        self.assertEqual(record.url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(record.title, "Rick Astley - Never Gonna Give You Up")
        self.assertEqual(record.channel.name, "Rick Astley")
        self.assertEqual(record.channel.id, "UCuAXFkgsw1L7xaCfnd5JJOw")
        self.assertEqual(record.thumbnail.url, "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg")
        self.assertEqual(record.duration_seconds, 212)
        self.assertEqual(record.upload_date, "2009-10-25")
        self.assertEqual(record.description, "The official video for Never Gonna Give You Up.")
        self.assertEqual(record.sources, ["watch_later"])
        self.assertEqual(record.source_positions, {"watch_later": 5, "liked": None})

    def test_normalize_missing_optional_fields(self):
        raw = {
            "id": "abc12345678",
            "title": "Minimal Video",
        }
        record = normalize_entry(raw, source_name="liked", position=1)
        self.assertIsNotNone(record)
        self.assertEqual(record.video_id, "abc12345678")
        self.assertIsNone(record.channel.name)
        self.assertIsNone(record.channel.id)
        self.assertIsNone(record.duration_seconds)
        self.assertIsNone(record.upload_date)
        self.assertIsNone(record.description)
        self.assertEqual(record.sources, ["liked"])
        self.assertEqual(record.source_positions, {"watch_later": None, "liked": 1})

    def test_normalize_raw_entries_list(self):
        raw_list = [
            {"id": "video111111", "title": "First"},
            None,
            {"id": "video222222", "title": "Second"},
            {"invalid": "no_id"},
        ]
        records = normalize_raw_entries(raw_list, source_name="watch_later")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].video_id, "video111111")
        self.assertEqual(records[0].source_positions["watch_later"], 1)
        self.assertEqual(records[1].video_id, "video222222")
        self.assertEqual(records[1].source_positions["watch_later"], 2)


if __name__ == "__main__":
    unittest.main()
