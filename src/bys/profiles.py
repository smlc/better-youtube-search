import re

from bys.youtube import Channel, Video

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
WHITESPACE_PATTERN = re.compile(r"\s+")

MAX_PROFILE_CHARS = 1500
MAX_CHANNEL_DESCRIPTION_CHARS = 500
MAX_VIDEO_DESCRIPTION_CHARS = 150


def clean_text(text: str) -> str:
    text = URL_PATTERN.sub(" ", text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def build_profile(channel: Channel, videos: list[Video]) -> str:
    parts = [f"{clean_text(channel.title)}."]
    channel_description = truncate(clean_text(channel.description), MAX_CHANNEL_DESCRIPTION_CHARS)
    if channel_description:
        parts.append(channel_description)
    if videos:
        titles = " | ".join(clean_text(video.title) for video in videos)
        parts.append(f"Recent videos: {titles}.")
    for video in videos:
        description = truncate(clean_text(video.description), MAX_VIDEO_DESCRIPTION_CHARS)
        if description:
            parts.append(description)
    return truncate(" ".join(parts), MAX_PROFILE_CHARS)
