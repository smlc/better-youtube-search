# bys (better-youtube-search)

Search your YouTube subscriptions by topic, for example "people who make videos about golang".

For each subscribed channel, `bys` stores the channel's name and description plus the title and description of its last 5 uploads. It embeds that profile with a small local model and ranks channels against your query.

## Setup

Requires Python 3.11 to 3.14 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --extra dev
```

### 1. Create Google credentials (one time)

1. Open the [Google Cloud console](https://console.cloud.google.com/) and create a project.
2. Enable the **YouTube Data API v3** for that project.
3. Configure the **OAuth consent screen**: user type *External*, and add your own Google account as a test user.
4. Create an **OAuth client ID** of type **Desktop app**, then download the JSON file.
5. Save it as `~/.bys/client_secret.json`.

Note: while the app is in "Testing" status, Google expires the login after about a week. If `bys sync` starts failing with "Stored login is no longer valid", run `bys login` again.

## Usage

```sh
uv run bys login                # sign in with your Google account (opens a browser)
uv run bys sync                 # fetch subscriptions and recent videos, then embed them
uv run bys search "golang"      # rank your channels by topic
uv run bys search "rust" -n 5   # show fewer results
```

`bys sync` only re-embeds channels whose profile changed, so repeat runs are fast.

Data lives in `~/.bys/` by default: `token.json` (your login), `client_secret.json`, and `bys.db`. Set `BYS_HOME` to use another directory.

## Development

```sh
uv run pytest
```
