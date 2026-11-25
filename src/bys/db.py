import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bys.youtube import Channel, Video

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    uploads_playlist_id TEXT,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS videos_channel_id ON videos(channel_id);
CREATE TABLE IF NOT EXISTS embeddings (
    channel_id TEXT PRIMARY KEY REFERENCES channels(id) ON DELETE CASCADE,
    profile TEXT NOT NULL,
    model TEXT NOT NULL,
    vector BLOB NOT NULL
);
"""


@dataclass(frozen=True)
class IndexedChannel:
    id: str
    title: str
    vector: np.ndarray
    recent_titles: list[str]


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_channel(
    conn: sqlite3.Connection, channel: Channel, videos: list[Video], synced_at: str
) -> None:
    conn.execute(
        """
        INSERT INTO channels (id, title, description, uploads_playlist_id, synced_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            uploads_playlist_id = excluded.uploads_playlist_id,
            synced_at = excluded.synced_at
        """,
        (
            channel.id,
            channel.title,
            channel.description,
            channel.uploads_playlist_id,
            synced_at,
        ),
    )
    conn.execute("DELETE FROM videos WHERE channel_id = ?", (channel.id,))
    conn.executemany(
        """
        INSERT INTO videos (id, channel_id, title, description, published_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(v.id, v.channel_id, v.title, v.description, v.published_at) for v in videos],
    )


def remove_unsubscribed(conn: sqlite3.Connection, keep_ids: list[str]) -> None:
    if not keep_ids:
        conn.execute("DELETE FROM channels")
        return
    placeholders = ",".join("?" * len(keep_ids))
    conn.execute(f"DELETE FROM channels WHERE id NOT IN ({placeholders})", keep_ids)


def stored_profiles(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT channel_id, profile FROM embeddings").fetchall()
    return {row["channel_id"]: row["profile"] for row in rows}


def save_embedding(
    conn: sqlite3.Connection, channel_id: str, profile: str, model: str, vector: np.ndarray
) -> None:
    conn.execute(
        """
        INSERT INTO embeddings (channel_id, profile, model, vector)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            profile = excluded.profile,
            model = excluded.model,
            vector = excluded.vector
        """,
        (channel_id, profile, model, vector.astype(np.float32).tobytes()),
    )


def load_index(conn: sqlite3.Connection) -> list[IndexedChannel]:
    rows = conn.execute(
        """
        SELECT c.id, c.title, e.vector
        FROM embeddings e JOIN channels c ON c.id = e.channel_id
        ORDER BY c.title
        """
    ).fetchall()
    indexed = []
    for row in rows:
        titles = conn.execute(
            "SELECT title FROM videos WHERE channel_id = ? ORDER BY published_at DESC",
            (row["id"],),
        ).fetchall()
        indexed.append(
            IndexedChannel(
                id=row["id"],
                title=row["title"],
                vector=np.frombuffer(row["vector"], dtype=np.float32),
                recent_titles=[t["title"] for t in titles],
            )
        )
    return indexed
