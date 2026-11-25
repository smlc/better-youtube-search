from dataclasses import dataclass

import numpy as np

from bys.db import IndexedChannel


@dataclass(frozen=True)
class Match:
    channel: IndexedChannel
    score: float


def top_matches(query: np.ndarray, channels: list[IndexedChannel], limit: int) -> list[Match]:
    if not channels:
        return []
    matrix = np.stack([channel.vector for channel in channels])
    scores = matrix @ query
    order = np.argsort(-scores)[:limit]
    return [Match(channel=channels[i], score=float(scores[i])) for i in order]
