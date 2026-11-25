from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from googleapiclient.discovery import build

UNAVAILABLE_TITLES = {"Deleted video", "Private video"}


@dataclass(frozen=True)
class Channel:
    id: str
    title: str
    description: str
    uploads_playlist_id: str | None


@dataclass(frozen=True)
class Video:
    id: str
    channel_id: str
    title: str
    description: str
    published_at: str


def build_client(credentials: Any) -> Any:
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def list_subscribed_channel_ids(client: Any) -> list[str]:
    items = _paginate(client.subscriptions().list, part="snippet", mine=True, maxResults=50)
    return [item["snippet"]["resourceId"]["channelId"] for item in items]


def fetch_channels(client: Any, channel_ids: list[str]) -> list[Channel]:
    channels = []
    for batch in _batches(channel_ids, 50):
        response = (
            client.channels()
            .list(part="snippet,contentDetails", id=",".join(batch), maxResults=50)
            .execute()
        )
        for item in response.get("items", []):
            snippet = item["snippet"]
            related = item.get("contentDetails", {}).get("relatedPlaylists", {})
            channels.append(
                Channel(
                    id=item["id"],
                    title=snippet["title"],
                    description=snippet.get("description", ""),
                    uploads_playlist_id=related.get("uploads"),
                )
            )
    return channels


def fetch_recent_videos(client: Any, channel: Channel, limit: int = 5) -> list[Video]:
    if not channel.uploads_playlist_id:
        return []
    response = (
        client.playlistItems()
        .list(
            part="snippet,contentDetails",
            playlistId=channel.uploads_playlist_id,
            maxResults=limit,
        )
        .execute()
    )
    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        if snippet.get("title") in UNAVAILABLE_TITLES:
            continue
        videos.append(
            Video(
                id=item["contentDetails"]["videoId"],
                channel_id=channel.id,
                title=snippet["title"],
                description=snippet.get("description", ""),
                published_at=snippet.get("publishedAt", ""),
            )
        )
    return videos


def _paginate(fetch: Callable[..., Any], **params: Any) -> Iterator[dict[str, Any]]:
    while True:
        response = fetch(**params).execute()
        yield from response.get("items", [])
        token = response.get("nextPageToken")
        if not token:
            return
        params["pageToken"] = token


def _batches(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
