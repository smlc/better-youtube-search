import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bys.auth import load_credentials
from bys.config import Paths
from bys.db import connect, remove_unsubscribed, save_channel, save_embedding, stored_profiles
from bys.embed import Embedder
from bys.profiles import build_profile
from bys.youtube import (
    Channel,
    Failure,
    build_client,
    describe_error,
    fetch_channels,
    fetch_recent_videos,
    list_subscribed_channel_ids,
)


@dataclass(frozen=True)
class SyncResult:
    channels: int
    reembedded: int
    failures: list[Failure]


def sync(paths: Paths, report: Callable[[str], None] = print) -> SyncResult:
    client = build_client(load_credentials(paths))

    channel_ids = list_subscribed_channel_ids(client)
    report(f"Found {len(channel_ids)} subscriptions")
    channels, failures = fetch_channels(client, channel_ids)

    synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = connect(paths.db)
    try:
        remove_unsubscribed(conn, channel_ids)
        conn.commit()

        profiles, channel_failures = sync_channels(conn, client, channels, synced_at, report)
        failures += channel_failures

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

    return SyncResult(channels=len(profiles), reembedded=len(pending), failures=failures)


def sync_channels(
    conn: sqlite3.Connection,
    client: Any,
    channels: list[Channel],
    synced_at: str,
    report: Callable[[str], None],
) -> tuple[dict[str, str], list[Failure]]:
    profiles = {}
    failures = []
    for index, channel in enumerate(channels, 1):
        report(f"[{index}/{len(channels)}] {channel.title}")
        try:
            videos = fetch_recent_videos(client, channel)
            save_channel(conn, channel, videos, synced_at)
            conn.commit()
        except Exception as error:
            conn.rollback()
            reason = describe_error(error)
            report(f"  failed: {reason}")
            failures.append(Failure(f"{channel.title} ({channel.id})", reason))
            continue
        profiles[channel.id] = build_profile(channel, videos)
    return profiles, failures
