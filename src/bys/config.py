import os
from dataclasses import dataclass
from pathlib import Path


class BysError(Exception):
    pass


@dataclass(frozen=True)
class Paths:
    home: Path

    @property
    def client_secret(self) -> Path:
        return self.home / "client_secret.json"

    @property
    def token(self) -> Path:
        return self.home / "token.json"

    @property
    def db(self) -> Path:
        return self.home / "bys.db"

    @property
    def failures_log(self) -> Path:
        return self.home / "sync-failures.log"


def default_paths() -> Paths:
    home = Path(os.environ.get("BYS_HOME", Path.home() / ".bys")).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    return Paths(home=home)
