"""
Unit tests for metadata normalization.
"""

import unittest
from scraper.normalize import (
    PlaylistRecord,
    PlaylistReference,
    extract_canonical_playlist_id,
    extract_canonical_video_id,
    format_upload_date,
    normalize_entry,
    normalize_playlist_info,
    normalize_raw_entries,
    pick_best_thumbnail_url,
)


class TestNormalize(unittest.TestCase):

    def test_extract_canonical_video_id(self):
        self.assertEqual(extract_canonical_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(
            extract_canonical_video_id(None, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_canonical_video_id(None, "https://youtu.be/dQw4w9WgXcQ?t=10"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_canonical_video_id(None, "https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertIsNone(extract_canonical_video_id(None, None))
        self.assertIsNone(extract_canonical_video_id("invalid", "https://google.com"))

    def test_extract_canonical_playlist_id(self):
        self.assertEqual(extract_canonical_playlist_id("PL1234567890"), "PL1234567890")
        self.assertEqual(extract_canonical_playlist_id("WL"), "WL")
        self.assertEqual(extract_canonical_playlist_id("LL"), "LL")
        self.assertEqual(
            extract_canonical_playlist_id(None, "https://www.youtube.com/playlist?list=PL1234567890"),
            "PL1234567890",
        )

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

    def test_normalize_entry_with_playlist_reference(self):
        raw = {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley in Playlist",
        }
        record = normalize_entry(
            raw,
            source_name="playlist:PL12345",
            position=2,
            playlist_id="PL12345",
            playlist_title="Pop Hits",
        )
        self.assertIsNotNone(record)
        self.assertIn("playlist:PL12345", record.sources)
        self.assertEqual(record.source_positions["PL12345"], 2)
        self.assertEqual(len(record.playlists), 1)
        self.assertEqual(record.playlists[0].id, "PL12345")
        self.assertEqual(record.playlists[0].title, "Pop Hits")
        self.assertEqual(record.playlists[0].position, 2)

    def test_normalize_playlist_info(self):
        raw_pl = {
            "id": "PL1234567890",
            "title": "Machine Learning",
            "description": "ML lecture series",
            "uploader": "DeepLearning AI",
            "uploader_id": "UC123",
            "playlist_count": 10,
        }
        pl_record = normalize_playlist_info(raw_pl, video_ids=["vid1", "vid2"])
        self.assertIsNotNone(pl_record)
        self.assertEqual(pl_record.playlist_id, "PL1234567890")
        self.assertEqual(pl_record.title, "Machine Learning")
        self.assertEqual(pl_record.url, "https://www.youtube.com/playlist?list=PL1234567890")
        self.assertEqual(pl_record.description, "ML lecture series")
        self.assertEqual(pl_record.channel.name, "DeepLearning AI")
        self.assertEqual(pl_record.video_ids, ["vid1", "vid2"])


if __name__ == "__main__":
    unittest.main()
