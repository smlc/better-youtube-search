import numpy as np

from bys.db import connect, load_index, remove_unsubscribed, save_channel, save_embedding, stored_profiles
from bys.youtube import Channel, Video


def make_channel(channel_id: str, title: str) -> Channel:
    return Channel(id=channel_id, title=title, description="", uploads_playlist_id=None)


def make_video(video_id: str, channel_id: str, title: str, published_at: str) -> Video:
    return Video(
        id=video_id,
        channel_id=channel_id,
        title=title,
        description="",
        published_at=published_at,
    )


def test_index_round_trip_returns_vectors_and_newest_titles_first(tmp_path):
    conn = connect(tmp_path / "bys.db")
    channel = make_channel("UC1", "Gopher Guy")
    save_channel(
        conn,
        channel,
        [
            make_video("v1", "UC1", "Old video", "2025-01-01T00:00:00Z"),
            make_video("v2", "UC1", "New video", "2026-01-01T00:00:00Z"),
        ],
        synced_at="2026-02-01T00:00:00+00:00",
    )
    vector = np.asarray([0.1, 0.2, 0.3], dtype=np.float32)
    save_embedding(conn, "UC1", "profile text", "model", vector)
    conn.commit()

    [indexed] = load_index(conn)

    assert indexed.title == "Gopher Guy"
    assert indexed.recent_titles == ["New video", "Old video"]
    assert np.allclose(indexed.vector, vector)
    assert stored_profiles(conn) == {"UC1": "profile text"}


def test_removing_unsubscribed_channels_also_drops_their_embeddings(tmp_path):
    conn = connect(tmp_path / "bys.db")
    for channel_id in ("UC1", "UC2"):
        save_channel(conn, make_channel(channel_id, channel_id), [], synced_at="now")
        save_embedding(conn, channel_id, "p", "model", np.ones(3, dtype=np.float32))
    conn.commit()

    remove_unsubscribed(conn, ["UC1"])
    conn.commit()

    assert [row["id"] for row in conn.execute("SELECT id FROM channels")] == ["UC1"]
    assert stored_profiles(conn) == {"UC1": "p"}
