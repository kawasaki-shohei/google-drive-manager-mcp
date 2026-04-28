from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .adapters.google_drive_adapter import GoogleDriveAdapter
from .adapters.oauth_flow import load_or_authorize
from .adapters.pandoc_adapter import PandocAdapter
from .application.use_cases import (
    CreateFolder,
    DeleteFile,
    ListFiles,
    ListFilesRequest,
    ListPermissions,
    ReadFile,
    RenameFile,
    RevokePermission,
    ShareFile,
    ShareFileRequest,
    UploadFile,
    UploadFileRequest,
    UploadCsvAsGoogleSheet,
    UploadCsvAsGoogleSheetRequest,
    UploadMarkdownAsGoogleDoc,
    UploadMarkdownAsGoogleDocRequest,
)
from .domain.models import DriveFile, Permission, PermissionRole

_mcp = FastMCP("google-drive-manager")


def _build_drive() -> GoogleDriveAdapter:
    creds = load_or_authorize()
    return GoogleDriveAdapter(credentials=creds)


@_mcp.tool()
def list_files(
    folder_id: str | None = None,
    name_contains: str | None = None,
    mime_type: str | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """List files in Google Drive with optional filters.

    Args:
        folder_id: Parent folder ID to scope the list. Omit to list across all folders.
        name_contains: Substring to match against file names.
        mime_type: Exact MIME type filter (e.g. 'text/csv', 'text/markdown', 'application/vnd.google-apps.folder').
        max_results: Maximum number of files to return (default 50).
    """
    drive = _build_drive()
    files = ListFiles(drive).execute(
        ListFilesRequest(
            folder_id=folder_id,
            query=name_contains,
            mime_type=mime_type,
            max_results=max_results,
        )
    )
    return [_file_to_dict(f) for f in files]


@_mcp.tool()
def read_file(file_id: str, encoding: str = "utf-8") -> str:
    """Read a Drive file's content as decoded text. Intended for MD, CSV, and other plain-text files.

    Args:
        file_id: Google Drive file ID.
        encoding: Text encoding used for decoding (default utf-8).
    """
    drive = _build_drive()
    result = ReadFile(drive).execute(file_id, encoding=encoding)
    assert isinstance(result, str)
    return result


@_mcp.tool()
def upload_file(
    local_path: str,
    parent_folder_id: str | None = None,
    name: str | None = None,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Upload a local file to Google Drive. The uploaded file is owned by the authenticated Google account.

    Args:
        local_path: Absolute path to the local file to upload.
        parent_folder_id: Destination folder ID. Optional.
        name: Override file name on Drive. Defaults to the local file name.
        mime_type: MIME type override (e.g. 'text/markdown', 'text/csv').
    """
    drive = _build_drive()
    created = UploadFile(drive).execute(
        UploadFileRequest(
            local_path=Path(local_path),
            parent_folder_id=parent_folder_id,
            name=name,
            mime_type=mime_type,
        )
    )
    return _file_to_dict(created)


@_mcp.tool()
def list_permissions(file_id: str) -> list[dict[str, Any]]:
    """List all sharing permissions on a Drive file.

    Args:
        file_id: Google Drive file ID.
    """
    drive = _build_drive()
    perms = ListPermissions(drive).execute(file_id)
    return [_permission_to_dict(p) for p in perms]


@_mcp.tool()
def share_file(
    file_id: str,
    email_address: str,
    role: str,
    notify: bool = False,
) -> dict[str, Any]:
    """Grant a sharing permission on a Drive file to a specific email address.

    Args:
        file_id: Google Drive file ID.
        email_address: Recipient email address to grant access to.
        role: Permission level. One of 'reader', 'commenter', 'writer'.
        notify: If True, send a notification email to the recipient (default False).
    """
    drive = _build_drive()
    perm = ShareFile(drive).execute(
        ShareFileRequest(
            file_id=file_id,
            email_address=email_address,
            role=PermissionRole(role),
            notify=notify,
        )
    )
    return _permission_to_dict(perm)


@_mcp.tool()
def revoke_permission(file_id: str, permission_id: str) -> dict[str, str]:
    """Remove a sharing permission from a Drive file.

    Args:
        file_id: Google Drive file ID.
        permission_id: Permission ID to revoke (retrieve via list_permissions).
    """
    drive = _build_drive()
    RevokePermission(drive).execute(file_id, permission_id)
    return {
        "status": "revoked",
        "file_id": file_id,
        "permission_id": permission_id,
    }


@_mcp.tool()
def delete_file(file_id: str) -> dict[str, str]:
    """Delete a file or folder from Google Drive permanently.

    Args:
        file_id: Google Drive file or folder ID to delete.
    """
    drive = _build_drive()
    DeleteFile(drive).execute(file_id)
    return {"status": "deleted", "file_id": file_id}


@_mcp.tool()
def rename_file(file_id: str, new_name: str) -> dict[str, Any]:
    """Rename a file or folder in Google Drive.

    Args:
        file_id: Google Drive file or folder ID to rename.
        new_name: New name to apply.
    """
    drive = _build_drive()
    updated = RenameFile(drive).execute(file_id=file_id, new_name=new_name)
    return _file_to_dict(updated)


@_mcp.tool()
def set_public_access(file_id: str, role: str = "writer") -> dict[str, str]:
    """Make a file accessible to anyone with the link.

    Args:
        file_id: Google Drive file or folder ID.
        role: Permission level. One of 'reader', 'commenter', 'writer' (default: writer).
    """
    drive = _build_drive()
    drive.make_anyone_with_link(file_id, role=role)
    return {"status": "public", "file_id": file_id, "role": role}


@_mcp.tool()
def upload_markdown_as_google_doc(
    md_path: str,
    drive_folder_id: str | None = None,
    doc_title: str | None = None,
) -> dict[str, Any]:
    """Convert a Markdown file (with local images) to Google Docs via pandoc and upload to Drive.

    Existing Google Docs with the same title in the target folder will be overwritten.
    If pandoc reports any warnings (e.g. missing image files), the upload is aborted.

    Args:
        md_path: Absolute path to the Markdown file.
        drive_folder_id: Destination Drive folder ID. Omit to place in Drive root.
        doc_title: Title for the Google Docs file. Defaults to the Markdown filename without extension.
    """
    drive = _build_drive()
    result = UploadMarkdownAsGoogleDoc(drive, PandocAdapter()).execute(
        UploadMarkdownAsGoogleDocRequest(
            md_path=Path(md_path),
            drive_folder_id=drive_folder_id,
            doc_title=doc_title,
        )
    )
    return _file_to_dict(result)


@_mcp.tool()
def upload_csv_as_google_sheet(
    csv_path: str,
    drive_folder_id: str | None = None,
    sheet_title: str | None = None,
) -> dict[str, Any]:
    """Upload a CSV file to Drive and convert it to a Google Sheets spreadsheet.

    Existing Google Sheets with the same title in the target folder will be overwritten.

    Args:
        csv_path: Absolute path to the CSV file.
        drive_folder_id: Destination Drive folder ID. Omit to place in Drive root.
        sheet_title: Title for the Google Sheets file. Defaults to the CSV filename without extension.
    """
    drive = _build_drive()
    result = UploadCsvAsGoogleSheet(drive).execute(
        UploadCsvAsGoogleSheetRequest(
            csv_path=Path(csv_path),
            drive_folder_id=drive_folder_id,
            sheet_title=sheet_title,
        )
    )
    return _file_to_dict(result)


@_mcp.tool()
def create_folder(
    name: str,
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    """Create a new folder in Google Drive.

    Args:
        name: Folder name.
        parent_folder_id: Parent folder ID. Omit to create in Drive root.
    """
    drive = _build_drive()
    folder = CreateFolder(drive).execute(name=name, parent_folder_id=parent_folder_id)
    return _file_to_dict(folder)


def _file_to_dict(f: DriveFile) -> dict[str, Any]:
    return {
        "id": f.id,
        "name": f.name,
        "mime_type": f.mime_type,
        "size": f.size,
        "parents": list(f.parents),
        "created_time": f.created_time.isoformat() if f.created_time else None,
        "modified_time": f.modified_time.isoformat() if f.modified_time else None,
        "web_view_link": f.web_view_link,
    }


def _permission_to_dict(p: Permission) -> dict[str, Any]:
    return {
        "id": p.id,
        "type": p.type.value,
        "role": p.role.value,
        "email_address": p.email_address,
        "display_name": p.display_name,
    }


def main() -> None:
    _mcp.run()


if __name__ == "__main__":
    main()
