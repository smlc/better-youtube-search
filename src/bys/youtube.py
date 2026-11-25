from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

UNAVAILABLE_TITLES = {"Deleted video", "Private video"}


@dataclass(frozen=True)
class Channel:
    id: str
    title: str
    description: str
    uploads_playlist_id: str | None


@dataclass(frozen=True)
class Failure:
    subject: str
    reason: str


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


def fetch_channels(client: Any, channel_ids: list[str]) -> tuple[list[Channel], list[Failure]]:
    channels = []
    failures = []
    for batch in _batches(channel_ids, 50):
        try:
            response = (
                client.channels()
                .list(part="snippet,contentDetails", id=",".join(batch), maxResults=50)
                .execute()
            )
        except Exception as error:
            failures.extend(Failure(channel_id, describe_error(error)) for channel_id in batch)
            continue
        returned_ids = set()
        for item in response.get("items", []):
            snippet = item["snippet"]
            related = item.get("contentDetails", {}).get("relatedPlaylists", {})
            returned_ids.add(item["id"])
            channels.append(
                Channel(
                    id=item["id"],
                    title=snippet["title"],
                    description=snippet.get("description", ""),
                    uploads_playlist_id=related.get("uploads"),
                )
            )
        failures.extend(
            Failure(channel_id, "not returned by the YouTube API")
            for channel_id in batch
            if channel_id not in returned_ids
        )
    return channels, failures


def describe_error(error: Exception) -> str:
    if isinstance(error, HttpError):
        return f"HTTP {error.resp.status}: {error.reason}"
    return f"{type(error).__name__}: {error}"


def fetch_recent_videos(client: Any, channel: Channel, limit: int = 5) -> list[Video]:
    if not channel.uploads_playlist_id:
        return []
    try:
        response = (
            client.playlistItems()
            .list(
                part="snippet,contentDetails",
                playlistId=channel.uploads_playlist_id,
                maxResults=limit,
            )
            .execute()
        )
    except HttpError as error:
        if error.resp.status == 404:
            return []
        raise
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
