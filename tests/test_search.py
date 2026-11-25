import numpy as np

from bys.db import IndexedChannel
from bys.search import top_matches


def make_channel(channel_id: str, vector: list[float]) -> IndexedChannel:
    return IndexedChannel(
        id=channel_id,
        title=channel_id,
        vector=np.asarray(vector, dtype=np.float32),
        recent_titles=[],
    )


def test_top_matches_orders_by_similarity():
    channels = [
        make_channel("cooking", [0.0, 1.0]),
        make_channel("go", [1.0, 0.0]),
        make_channel("rust", [0.8, 0.6]),
    ]
    query = np.asarray([1.0, 0.0], dtype=np.float32)

    matches = top_matches(query, channels, limit=2)

    assert [match.channel.id for match in matches] == ["go", "rust"]
    assert matches[0].score > matches[1].score


def test_top_matches_respects_limit_and_handles_empty_index():
    query = np.asarray([1.0, 0.0], dtype=np.float32)
    assert top_matches(query, [], limit=5) == []
    assert len(top_matches(query, [make_channel("a", [1.0, 0.0])], limit=5)) == 1
