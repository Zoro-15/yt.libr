"""
Unit tests for deduplication.
"""

import unittest
from scraper.normalize import ChannelInfo, ThumbnailInfo, VideoRecord
from scraper.deduplicate import deduplicate_records


class TestDeduplicate(unittest.TestCase):

    def setUp(self):
        self.record1 = VideoRecord(
            video_id="video111111",
            url="https://www.youtube.com/watch?v=video111111",
            title="Video 1",
            channel=ChannelInfo(name="Channel 1", id="UC1"),
            thumbnail=ThumbnailInfo(url="https://img/1.jpg"),
            duration_seconds=100,
            upload_date="2025-01-01",
            description="Desc 1",
            sources=["watch_later"],
            source_positions={"watch_later": 1, "liked": None},
        )
        self.record2 = VideoRecord(
            video_id="video222222",
            url="https://www.youtube.com/watch?v=video222222",
            title="Video 2",
            channel=ChannelInfo(name="Channel 2", id="UC2"),
            thumbnail=ThumbnailInfo(url="https://img/2.jpg"),
            duration_seconds=200,
            upload_date="2025-01-02",
            description="Desc 2",
            sources=["watch_later"],
            source_positions={"watch_later": 2, "liked": None},
        )
        # Duplicate of record 1
        self.record1_dup = VideoRecord(
            video_id="video111111",
            url="https://www.youtube.com/watch?v=video111111",
            title="Video 1 Duplicate",
            channel=ChannelInfo(name="Channel 1", id="UC1"),
            thumbnail=ThumbnailInfo(url="https://img/1.jpg"),
            duration_seconds=100,
            upload_date="2025-01-01",
            description="Desc 1",
            sources=["liked"],
            source_positions={"watch_later": None, "liked": 10},
        )

    def test_no_duplicates(self):
        records = [self.record1, self.record2]
        unique, count = deduplicate_records(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual(count, 0)
        self.assertEqual(unique[0].video_id, "video111111")
        self.assertEqual(unique[1].video_id, "video222222")

    def test_duplicate_removal_and_source_merging(self):
        records = [self.record1, self.record2, self.record1_dup]
        unique, count = deduplicate_records(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual(count, 1)

        # First record should now have both sources and both positions
        self.assertEqual(unique[0].video_id, "video111111")
        self.assertIn("watch_later", unique[0].sources)
        self.assertIn("liked", unique[0].sources)
        self.assertEqual(unique[0].source_positions["watch_later"], 1)
        self.assertEqual(unique[0].source_positions["liked"], 10)


if __name__ == "__main__":
    unittest.main()
