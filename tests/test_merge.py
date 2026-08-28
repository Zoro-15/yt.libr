"""
Unit tests for multi-source merging (Watch Later, Liked, and Playlists).
"""

import unittest
from scraper.normalize import (
    ChannelInfo,
    PlaylistRecord,
    PlaylistReference,
    ThumbnailInfo,
    VideoRecord,
)
from scraper.merge import merge_single_record, merge_sources


def make_test_record(
    vid: str,
    source: str,
    pos: int,
    title: str = "Title",
    channel_name: str = "Channel",
    description: str = "Description",
    playlist_id: str = None,
    playlist_title: str = None,
) -> VideoRecord:
    playlists = []
    source_positions = {
        "watch_later": pos if source == "watch_later" else None,
        "liked": pos if source == "liked" else None,
    }
    if playlist_id:
        source_positions[playlist_id] = pos
        playlists.append(PlaylistReference(id=playlist_id, title=playlist_title or playlist_id, position=pos))

    return VideoRecord(
        video_id=vid,
        url=f"https://www.youtube.com/watch?v={vid}",
        title=title,
        channel=ChannelInfo(name=channel_name, id=f"UC_{vid}"),
        thumbnail=ThumbnailInfo(url=f"https://img/{vid}.jpg"),
        duration_seconds=120,
        upload_date="2025-01-01",
        description=description,
        sources=[source],
        source_positions=source_positions,
        playlists=playlists,
    )


class TestMerge(unittest.TestCase):

    def test_merge_single_record_field_enrichment(self):
        base = VideoRecord(
            video_id="video111111",
            url="https://www.youtube.com/watch?v=video111111",
            title="Video 1",
            channel=ChannelInfo(name="Channel 1", id=None),
            thumbnail=ThumbnailInfo(url=None),
            duration_seconds=100,
            upload_date=None,
            description=None,
            sources=["watch_later"],
            source_positions={"watch_later": 1, "liked": None},
        )
        incoming = VideoRecord(
            video_id="video111111",
            url="https://www.youtube.com/watch?v=video111111",
            title=None,
            channel=ChannelInfo(name=None, id="UC_REAL_ID"),
            thumbnail=ThumbnailInfo(url="https://img/real.jpg"),
            duration_seconds=100,
            upload_date="2025-02-01",
            description="Enriched description",
            sources=["liked"],
            source_positions={"watch_later": None, "liked": 5},
        )

        merged = merge_single_record(base, incoming)
        self.assertEqual(merged.title, "Video 1")
        self.assertEqual(merged.channel.name, "Channel 1")
        self.assertEqual(merged.channel.id, "UC_REAL_ID")
        self.assertEqual(merged.thumbnail.url, "https://img/real.jpg")
        self.assertEqual(merged.upload_date, "2025-02-01")
        self.assertEqual(merged.description, "Enriched description")
        self.assertEqual(merged.sources, ["liked", "watch_later"])
        self.assertEqual(merged.source_positions, {"watch_later": 1, "liked": 5})

    def test_merge_overlapping_sources(self):
        wl_records = [
            make_test_record("vid_A", "watch_later", 1),
            make_test_record("vid_B", "watch_later", 2),
        ]
        liked_records = [
            make_test_record("vid_B", "liked", 1),
            make_test_record("vid_C", "liked", 2),
        ]

        merged, playlists, summary = merge_sources(wl_records, liked_records)

        self.assertEqual(len(merged), 3)
        self.assertEqual(summary.total_watch_later, 2)
        self.assertEqual(summary.total_liked, 2)
        self.assertEqual(summary.total_unique, 3)
        self.assertEqual(summary.overlap_count, 1)

        # Video A
        self.assertEqual(merged[0].video_id, "vid_A")
        self.assertEqual(merged[0].sources, ["watch_later"])

        # Video B
        self.assertEqual(merged[1].video_id, "vid_B")
        self.assertEqual(merged[1].sources, ["liked", "watch_later"])

        # Video C
        self.assertEqual(merged[2].video_id, "vid_C")
        self.assertEqual(merged[2].sources, ["liked"])

    def test_merge_with_custom_playlists(self):
        wl = [make_test_record("vid_A", "watch_later", 1)]
        liked = [make_test_record("vid_B", "liked", 1)]
        custom_pl = {
            "PL123": [
                make_test_record("vid_A", "playlist:PL123", 1, playlist_id="PL123", playlist_title="Favorites"),
                make_test_record("vid_D", "playlist:PL123", 2, playlist_id="PL123", playlist_title="Favorites"),
            ]
        }

        merged, playlists, summary = merge_sources(wl, liked, custom_playlist_records=custom_pl)

        self.assertEqual(len(merged), 3)  # vid_A (in WL and PL123), vid_B (in Liked), vid_D (in PL123)
        self.assertEqual(summary.total_unique, 3)
        self.assertEqual(summary.total_custom_playlists, 1)
        self.assertEqual(len(playlists), 1)

        # Check vid_A playlist references
        vid_a = next(v for v in merged if v.video_id == "vid_A")
        self.assertIn("watch_later", vid_a.sources)
        self.assertIn("playlist:PL123", vid_a.sources)
        self.assertEqual(len(vid_a.playlists), 1)
        self.assertEqual(vid_a.playlists[0].id, "PL123")


if __name__ == "__main__":
    unittest.main()
