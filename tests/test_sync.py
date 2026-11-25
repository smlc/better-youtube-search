import httplib2
from googleapiclient.errors import HttpError

from bys.db import connect
from bys.sync import sync_channels
from bys.youtube import Channel


class PlaylistClient:
    """Fails with HTTP 403 for playlist UU2 and returns no videos for the others."""

    def playlistItems(self):
        return self

    def list(self, playlistId, **params):
        return _Request(playlistId)


class _Request:
    def __init__(self, playlist_id):
        self._playlist_id = playlist_id

    def execute(self):
        if self._playlist_id == "UU2":
            response = httplib2.Response({"status": 403})
            raise HttpError(response, b'{"error": {"message": "forbidden"}}')
        return {"items": []}


def make_channel(channel_id: str) -> Channel:
    return Channel(
        id=channel_id,
        title=f"Channel {channel_id}",
        description="",
        uploads_playlist_id=f"UU{channel_id[-1]}",
    )


def test_sync_channels_skips_a_failing_channel_and_keeps_the_rest(tmp_path):
    conn = connect(tmp_path / "bys.db")
    channels = [make_channel("UC1"), make_channel("UC2"), make_channel("UC3")]
    reports = []

    profiles, failures = sync_channels(
        conn, PlaylistClient(), channels, "now", report=reports.append
    )

    assert set(profiles) == {"UC1", "UC3"}
    assert [row["id"] for row in conn.execute("SELECT id FROM channels ORDER BY id")] == [
        "UC1",
        "UC3",
    ]
    [failure] = failures
    assert failure.subject == "Channel UC2 (UC2)"
    assert "HTTP 403" in failure.reason
    assert any("failed" in line for line in reports)
