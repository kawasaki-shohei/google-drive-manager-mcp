import os
from pathlib import Path


def _base_dir() -> Path:
    env_path = os.environ.get("GOOGLE_DRIVE_MANAGER_HOME")
    if env_path:
        return Path(env_path)
    return Path.home() / ".claude" / "mcp-servers" / "google-drive-manager"


def credentials_dir() -> Path:
    return _base_dir() / "credentials"


def client_secrets_path() -> Path:
    return credentials_dir() / "client_secrets.json"


def token_path() -> Path:
    return credentials_dir() / "token.json"


SCOPES: list[str] = ["https://www.googleapis.com/auth/drive"]
