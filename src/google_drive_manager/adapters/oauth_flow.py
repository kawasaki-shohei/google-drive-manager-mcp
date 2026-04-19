import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import SCOPES, client_secrets_path, credentials_dir, token_path


def load_or_authorize() -> Credentials:
    creds: Credentials | None = None
    token_file = token_path()
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds, token_file)
        return creds

    secrets = client_secrets_path()
    if not secrets.exists():
        raise FileNotFoundError(
            f"OAuth client secrets not found at {secrets}. "
            "Download the Desktop OAuth client JSON from GCP and place it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    _save_token(creds, token_file)
    return creds


def _save_token(creds: Credentials, path: Path) -> None:
    credentials_dir().mkdir(mode=0o700, exist_ok=True)
    path.write_text(creds.to_json())
    path.chmod(0o600)


def main() -> int:
    try:
        creds = load_or_authorize()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Authorized. Token saved to {token_path()}")
    print(f"Valid: {creds.valid}, Scopes: {creds.scopes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
