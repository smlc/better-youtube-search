import httplib2
import pytest
from googleapiclient.errors import HttpError

from bys.youtube import (
    Channel,
    fetch_channels,
    fetch_recent_videos,
    list_subscribed_channel_ids,
)


class FakeRequest:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class FakeResource:
    """Returns the queued responses in order, recording the params of each call."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = []

    def list(self, **params):
        self.calls.append(params)
        return FakeRequest(self._responses.pop(0))


class FakeClient:
    def __init__(self, subscriptions=None, channels=None, playlist_items=None):
        self._resources = {
            "subscriptions": subscriptions or FakeResource(),
            "channels": channels or FakeResource(),
            "playlistItems": playlist_items or FakeResource(),
        }

    def subscriptions(self):
        return self._resources["subscriptions"]

    def channels(self):
        return self._resources["channels"]

    def playlistItems(self):
        return self._resources["playlistItems"]


def test_list_subscribed_channel_ids_follows_pagination():
    subscriptions = FakeResource(
        {
            "items": [{"snippet": {"resourceId": {"channelId": "UC1"}}}],
            "nextPageToken": "page2",
        },
        {"items": [{"snippet": {"resourceId": {"channelId": "UC2"}}}]},
    )

    ids = list_subscribed_channel_ids(FakeClient(subscriptions=subscriptions))

    assert ids == ["UC1", "UC2"]
    assert subscriptions.calls[1]["pageToken"] == "page2"


def test_fetch_channels_reads_title_description_and_uploads_playlist():
    channels = FakeResource(
        {
            "items": [
                {
                    "id": "UC1",
                    "snippet": {"title": "Gopher Guy", "description": "Go videos"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}},
                }
            ]
        }
    )

    [channel], failures = fetch_channels(FakeClient(channels=channels), ["UC1"])

    assert channel == Channel(
        id="UC1", title="Gopher Guy", description="Go videos", uploads_playlist_id="UU1"
    )
    assert failures == []


def test_fetch_channels_reports_channels_the_api_did_not_return():
    channels = FakeResource(
        {
            "items": [
                {
                    "id": "UC1",
                    "snippet": {"title": "Gopher Guy"},
                    "contentDetails": {},
                }
            ]
        }
    )

    channels_found, failures = fetch_channels(FakeClient(channels=channels), ["UC1", "UC2"])

    assert [channel.id for channel in channels_found] == ["UC1"]
    assert [failure.subject for failure in failures] == ["UC2"]


def test_fetch_channels_records_failed_batch_and_continues_with_next_one():
    ids = [f"UC{i}" for i in range(51)]

    class FailFirstBatch:
        def __init__(self):
            self.calls = 0

        def list(self, **params):
            self.calls += 1
            if self.calls == 1:
                return FailingRequest(500)
            return FakeRequest({"items": [{"id": "UC50", "snippet": {"title": "x"}}]})

    channels_found, failures = fetch_channels(
        FakeClient(channels=FailFirstBatch()), ids
    )

    assert [channel.id for channel in channels_found] == ["UC50"]
    assert len(failures) == 50
    assert failures[0].subject == "UC0"
    assert "HTTP 500" in failures[0].reason


def test_fetch_recent_videos_skips_deleted_and_private_videos():
    playlist_items = FakeResource(
        {
            "items": [
                {
                    "snippet": {
                        "title": "Goroutines",
                        "description": "d",
                        "publishedAt": "2026-01-02T00:00:00Z",
                    },
                    "contentDetails": {"videoId": "v1"},
                },
                {
                    "snippet": {"title": "Private video", "description": ""},
                    "contentDetails": {"videoId": "v2"},
                },
                {
                    "snippet": {"title": "Deleted video", "description": ""},
                    "contentDetails": {"videoId": "v3"},
                },
            ]
        }
    )
    channel = Channel(id="UC1", title="Gopher Guy", description="", uploads_playlist_id="UU1")

    videos = fetch_recent_videos(FakeClient(playlist_items=playlist_items), channel, limit=5)

    assert [video.id for video in videos] == ["v1"]
    assert playlist_items.calls[0]["playlistId"] == "UU1"
    assert playlist_items.calls[0]["maxResults"] == 5


class FailingRequest:
    def __init__(self, status):
        self._status = status

    def execute(self):
        response = httplib2.Response({"status": self._status})
        raise HttpError(response, b'{"error": {"message": "not found"}}')


class FailingResource:
    def __init__(self, status):
        self._status = status

    def list(self, **params):
        return FailingRequest(self._status)


def test_fetch_recent_videos_returns_empty_when_playlist_not_found():
    channel = Channel(id="UC1", title="x", description="", uploads_playlist_id="UU1")
    client = FakeClient(playlist_items=FailingResource(404))

    assert fetch_recent_videos(client, channel) == []


def test_fetch_recent_videos_still_raises_other_errors():
    channel = Channel(id="UC1", title="x", description="", uploads_playlist_id="UU1")
    client = FakeClient(playlist_items=FailingResource(403))

    with pytest.raises(HttpError):
        fetch_recent_videos(client, channel)


def test_fetch_recent_videos_without_uploads_playlist_makes_no_call():
    playlist_items = FakeResource()
    channel = Channel(id="UC1", title="x", description="", uploads_playlist_id=None)

    assert fetch_recent_videos(FakeClient(playlist_items=playlist_items), channel) == []
    assert playlist_items.calls == []
