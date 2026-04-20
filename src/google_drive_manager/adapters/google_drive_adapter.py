from datetime import datetime
from io import BytesIO
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from ..domain.models import DriveFile, Permission, PermissionRole, PermissionType
from ..domain.ports import DrivePort

_FILE_FIELDS = "id,name,mimeType,size,parents,createdTime,modifiedTime,webViewLink"
_FILES_LIST_FIELDS = f"files({_FILE_FIELDS}),nextPageToken"
_PERMISSION_FIELDS = "id,type,role,emailAddress,displayName"
_PERMISSIONS_LIST_FIELDS = f"permissions({_PERMISSION_FIELDS})"
_GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class GoogleDriveAdapter(DrivePort):
    def __init__(self, credentials: Credentials) -> None:
        self._service = build(
            "drive", "v3", credentials=credentials, cache_discovery=False
        )

    def list_files(
        self,
        folder_id: str | None,
        query: str | None,
        mime_type: str | None,
        max_results: int,
    ) -> list[DriveFile]:
        q_parts: list[str] = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if mime_type:
            q_parts.append(f"mimeType = '{mime_type}'")
        if query:
            escaped = query.replace("'", "\\'")
            q_parts.append(f"name contains '{escaped}'")
        q = " and ".join(q_parts)

        resp = (
            self._service.files()
            .list(
                q=q,
                pageSize=max_results,
                fields=_FILES_LIST_FIELDS,
                supportsAllDrives=False,
            )
            .execute()
        )
        return [_to_drive_file(f) for f in resp.get("files", [])]

    def read_file_bytes(self, file_id: str) -> bytes:
        meta = self._service.files().get(fileId=file_id, fields="mimeType").execute()
        if meta.get("mimeType") == _GOOGLE_DOC_MIME:
            return self._service.files().export(
                fileId=file_id, mimeType="text/plain"
            ).execute()
        request = self._service.files().get_media(fileId=file_id)
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def upload_file(
        self,
        local_path: Path,
        parent_folder_id: str | None,
        name: str | None,
        mime_type: str | None,
    ) -> DriveFile:
        body: dict[str, object] = {"name": name or local_path.name}
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=False)
        created = (
            self._service.files()
            .create(body=body, media_body=media, fields=_FILE_FIELDS)
            .execute()
        )
        return _to_drive_file(created)

    def list_permissions(self, file_id: str) -> list[Permission]:
        resp = (
            self._service.permissions()
            .list(fileId=file_id, fields=_PERMISSIONS_LIST_FIELDS)
            .execute()
        )
        return [_to_permission(p) for p in resp.get("permissions", [])]

    def share_file(
        self,
        file_id: str,
        email_address: str,
        role: PermissionRole,
        notify: bool,
    ) -> Permission:
        body = {
            "type": PermissionType.USER.value,
            "role": role.value,
            "emailAddress": email_address,
        }
        created = (
            self._service.permissions()
            .create(
                fileId=file_id,
                body=body,
                sendNotificationEmail=notify,
                fields=_PERMISSION_FIELDS,
            )
            .execute()
        )
        return _to_permission(created)

    def revoke_permission(self, file_id: str, permission_id: str) -> None:
        self._service.permissions().delete(
            fileId=file_id, permissionId=permission_id
        ).execute()

    def delete_file(self, file_id: str) -> None:
        self._service.files().delete(fileId=file_id).execute()

    def rename_file(self, file_id: str, new_name: str) -> DriveFile:
        updated = (
            self._service.files()
            .update(fileId=file_id, body={"name": new_name}, fields=_FILE_FIELDS)
            .execute()
        )
        return _to_drive_file(updated)

    def find_google_doc_by_name(
        self, name: str, parent_folder_id: str | None
    ) -> DriveFile | None:
        escaped = name.replace("'", "\\'")
        q_parts = [
            f"name = '{escaped}'",
            f"mimeType = '{_GOOGLE_DOC_MIME}'",
            "trashed = false",
        ]
        if parent_folder_id:
            q_parts.append(f"'{parent_folder_id}' in parents")
        resp = (
            self._service.files()
            .list(q=" and ".join(q_parts), fields=f"files({_FILE_FIELDS})", pageSize=1)
            .execute()
        )
        files = resp.get("files", [])
        return _to_drive_file(files[0]) if files else None

    def upload_as_google_doc(
        self,
        docx_path: Path,
        title: str,
        parent_folder_id: str | None,
    ) -> DriveFile:
        body: dict[str, object] = {"name": title, "mimeType": _GOOGLE_DOC_MIME}
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        media = MediaFileUpload(str(docx_path), mimetype=_DOCX_MIME, resumable=False)
        created = (
            self._service.files()
            .create(body=body, media_body=media, fields=_FILE_FIELDS)
            .execute()
        )
        return _to_drive_file(created)

    def update_google_doc_content(
        self,
        file_id: str,
        docx_path: Path,
        title: str,
    ) -> DriveFile:
        media = MediaFileUpload(str(docx_path), mimetype=_DOCX_MIME, resumable=False)
        updated = (
            self._service.files()
            .update(
                fileId=file_id,
                body={"name": title},
                media_body=media,
                fields=_FILE_FIELDS,
            )
            .execute()
        )
        return _to_drive_file(updated)

    def make_anyone_with_link(self, file_id: str, role: str = "writer") -> None:
        self._service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": role},
            fields="id",
        ).execute()

    def create_folder(self, name: str, parent_folder_id: str | None) -> DriveFile:
        body: dict[str, object] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        created = (
            self._service.files()
            .create(body=body, fields=_FILE_FIELDS)
            .execute()
        )
        return _to_drive_file(created)


def _to_drive_file(raw: dict) -> DriveFile:
    return DriveFile(
        id=raw["id"],
        name=raw["name"],
        mime_type=raw["mimeType"],
        size=int(raw["size"]) if "size" in raw else None,
        parents=tuple(raw.get("parents", [])),
        created_time=_parse_time(raw.get("createdTime")),
        modified_time=_parse_time(raw.get("modifiedTime")),
        web_view_link=raw.get("webViewLink"),
    )


def _to_permission(raw: dict) -> Permission:
    return Permission(
        id=raw["id"],
        type=PermissionType(raw["type"]),
        role=PermissionRole(raw["role"]),
        email_address=raw.get("emailAddress"),
        display_name=raw.get("displayName"),
    )


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
