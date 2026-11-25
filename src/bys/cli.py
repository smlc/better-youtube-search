import argparse
import sys
from datetime import datetime, timezone

from googleapiclient.errors import HttpError

from bys.auth import login
from bys.config import BysError, Paths, default_paths
from bys.db import connect, load_index
from bys.embed import Embedder
from bys.search import top_matches
from bys.sync import sync
from bys.youtube import Failure

RECENT_TITLES_SHOWN = 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bys", description="Search your YouTube subscriptions by topic."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="sign in with your Google account")
    commands.add_parser("sync", help="fetch subscriptions and recent videos, then index them")
    search = commands.add_parser("search", help="find channels that match a topic")
    search.add_argument("query", help='e.g. "people who make videos about golang"')
    search.add_argument("-n", "--limit", type=int, default=10, help="number of results")
    args = parser.parse_args(argv)

    paths = default_paths()
    try:
        if args.command == "login":
            login(paths)
            print("Logged in.")
        elif args.command == "sync":
            return _sync(paths)
        elif args.command == "search":
            return _search(paths, args.query, args.limit)
    except BysError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except HttpError as error:
        print(f"YouTube API error: {error}", file=sys.stderr)
        return 1
    return 0


def _sync(paths: Paths) -> int:
    result = sync(paths)
    print(f"Synced {result.channels} channels, re-embedded {result.reembedded}.")
    if result.failures:
        _log_failures(paths, result.failures)
        print(
            f"{len(result.failures)} failed (logged to {paths.failures_log}):",
            file=sys.stderr,
        )
        for failure in result.failures:
            print(f"  - {failure.subject}: {failure.reason}", file=sys.stderr)
    return 0


def _log_failures(paths: Paths, failures: list[Failure]) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with paths.failures_log.open("a") as log:
        for failure in failures:
            log.write(f"{stamp}\t{failure.subject}\t{failure.reason}\n")


def _search(paths: Paths, query: str, limit: int) -> int:
    conn = connect(paths.db)
    try:
        channels = load_index(conn)
    finally:
        conn.close()
    if not channels:
        raise BysError("Nothing indexed yet. Run `bys sync` first.")

    matches = top_matches(Embedder().embed_query(query), channels, limit)
    for rank, match in enumerate(matches, 1):
        channel = match.channel
        print(f"{rank}. {channel.title}  ({match.score:.2f})")
        print(f"   https://www.youtube.com/channel/{channel.id}")
        for title in channel.recent_titles[:RECENT_TITLES_SHOWN]:
            print(f"   - {title}")
    return 0
