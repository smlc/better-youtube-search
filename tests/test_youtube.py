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

    [channel] = fetch_channels(FakeClient(channels=channels), ["UC1"])

    assert channel == Channel(
        id="UC1", title="Gopher Guy", description="Go videos", uploads_playlist_id="UU1"
    )


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


def test_fetch_recent_videos_without_uploads_playlist_makes_no_call():
    playlist_items = FakeResource()
    channel = Channel(id="UC1", title="x", description="", uploads_playlist_id=None)

    assert fetch_recent_videos(FakeClient(playlist_items=playlist_items), channel) == []
    assert playlist_items.calls == []
