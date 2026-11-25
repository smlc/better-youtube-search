from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from bys.config import BysError, Paths

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def login(paths: Paths) -> Credentials:
    if not paths.client_secret.exists():
        raise BysError(
            f"Missing {paths.client_secret}. See README.md for how to create it."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(paths.client_secret), SCOPES)
    creds = flow.run_local_server(port=0)
    _save(creds, paths)
    return creds


def load_credentials(paths: Paths) -> Credentials:
    if not paths.token.exists():
        raise BysError("Not logged in. Run `bys login` first.")
    creds = Credentials.from_authorized_user_file(str(paths.token), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save(creds, paths)
        return creds
    raise BysError("Stored login is no longer valid. Run `bys login` again.")


def _save(creds: Credentials, paths: Paths) -> None:
    paths.token.write_text(creds.to_json())
