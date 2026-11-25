from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from bys.auth import load_credentials
from bys.config import Paths
from bys.db import connect, remove_unsubscribed, save_channel, save_embedding, stored_profiles
from bys.embed import Embedder
from bys.profiles import build_profile
from bys.youtube import (
    build_client,
    fetch_channels,
    fetch_recent_videos,
    list_subscribed_channel_ids,
)


@dataclass(frozen=True)
class SyncResult:
    channels: int
    reembedded: int


def sync(paths: Paths, report: Callable[[str], None] = print) -> SyncResult:
    client = build_client(load_credentials(paths))

    channel_ids = list_subscribed_channel_ids(client)
    report(f"Found {len(channel_ids)} subscriptions")
    channels = fetch_channels(client, channel_ids)

    synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = connect(paths.db)
    try:
        remove_unsubscribed(conn, [channel.id for channel in channels])
        profiles = {}
        for index, channel in enumerate(channels, 1):
            report(f"[{index}/{len(channels)}] {channel.title}")
            videos = fetch_recent_videos(client, channel)
            save_channel(conn, channel, videos, synced_at)
            profiles[channel.id] = build_profile(channel, videos)
        conn.commit()

        current = stored_profiles(conn)
        pending = [(cid, text) for cid, text in profiles.items() if current.get(cid) != text]
        if pending:
            report(f"Embedding {len(pending)} changed channels")
            embedder = Embedder()
            vectors = embedder.embed_documents([text for _, text in pending])
            for (cid, text), vector in zip(pending, vectors):
                save_embedding(conn, cid, text, embedder.model_name, vector)
            conn.commit()
    finally:
        conn.close()

    return SyncResult(channels=len(channels), reembedded=len(pending))
