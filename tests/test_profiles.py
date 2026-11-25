from bys.profiles import MAX_PROFILE_CHARS, build_profile, clean_text
from bys.youtube import Channel, Video


def make_channel(description: str = "") -> Channel:
    return Channel(id="UC1", title="Gopher Guy", description=description, uploads_playlist_id="UU1")


def make_video(title: str, description: str = "") -> Video:
    return Video(
        id=title,
        channel_id="UC1",
        title=title,
        description=description,
        published_at="2026-01-01T00:00:00Z",
    )


def test_clean_text_removes_urls_and_extra_whitespace():
    text = "Check   https://example.com/x \n\n and www.foo.com  now"
    assert clean_text(text) == "Check and now"


def test_profile_contains_channel_and_recent_titles():
    profile = build_profile(
        make_channel("I make Go tutorials."),
        [make_video("Goroutines explained"), make_video("Generics in Go")],
    )
    assert profile.startswith("Gopher Guy. I make Go tutorials.")
    assert "Recent videos: Goroutines explained | Generics in Go." in profile


def test_profile_without_videos_or_description_is_just_the_title():
    assert build_profile(make_channel(), []) == "Gopher Guy."


def test_profile_truncates_long_descriptions_but_keeps_video_titles():
    long_description = "word " * 1000
    profile = build_profile(
        make_channel(long_description),
        [make_video("Goroutines explained", long_description)],
    )
    assert len(profile) <= MAX_PROFILE_CHARS
    assert "Recent videos: Goroutines explained." in profile
