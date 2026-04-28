from pathlib import Path
from uuid import uuid4

from google_drive_manager.domain.models import (
    DriveFile,
    Permission,
    PermissionRole,
    PermissionType,
)
from google_drive_manager.domain.ports import DrivePort, PandocConverterPort


class FakePandocConverter(PandocConverterPort):
    def __init__(
        self,
        warnings: list[str] | None = None,
        raise_error: str | None = None,
    ) -> None:
        self._warnings = warnings or []
        self._raise_error = raise_error

    def convert_md_to_docx(self, md_path: Path, output_path: Path) -> list[str]:
        if self._raise_error:
            raise RuntimeError(self._raise_error)
        output_path.write_bytes(b"fake docx content")
        return self._warnings


class FakeDrivePort(DrivePort):
    def __init__(self) -> None:
        self._files: dict[str, DriveFile] = {}
        self._file_bytes: dict[str, bytes] = {}
        self._permissions: dict[str, list[Permission]] = {}

    def seed_file(self, file: DriveFile, content: bytes = b"") -> None:
        self._files[file.id] = file
        self._file_bytes[file.id] = content
        self._permissions.setdefault(file.id, [])

    def list_files(
        self,
        folder_id: str | None,
        query: str | None,
        mime_type: str | None,
        max_results: int,
    ) -> list[DriveFile]:
        results = list(self._files.values())
        if folder_id:
            results = [f for f in results if folder_id in f.parents]
        if mime_type:
            results = [f for f in results if f.mime_type == mime_type]
        if query:
            results = [f for f in results if query in f.name]
        return results[:max_results]

    def read_file_bytes(self, file_id: str) -> bytes:
        if file_id not in self._file_bytes:
            raise FileNotFoundError(file_id)
        return self._file_bytes[file_id]

    def upload_file(
        self,
        local_path: Path,
        parent_folder_id: str | None,
        name: str | None,
        mime_type: str | None,
    ) -> DriveFile:
        new_id = str(uuid4())
        file = DriveFile(
            id=new_id,
            name=name or local_path.name,
            mime_type=mime_type or "application/octet-stream",
            size=local_path.stat().st_size if local_path.exists() else 0,
            parents=(parent_folder_id,) if parent_folder_id else (),
            created_time=None,
            modified_time=None,
            web_view_link=None,
        )
        self._files[new_id] = file
        self._file_bytes[new_id] = (
            local_path.read_bytes() if local_path.exists() else b""
        )
        self._permissions[new_id] = []
        return file

    def list_permissions(self, file_id: str) -> list[Permission]:
        if file_id not in self._permissions:
            raise FileNotFoundError(file_id)
        return list(self._permissions[file_id])

    def share_file(
        self,
        file_id: str,
        email_address: str,
        role: PermissionRole,
        notify: bool,
    ) -> Permission:
        if file_id not in self._permissions:
            raise FileNotFoundError(file_id)
        permission = Permission(
            id=str(uuid4()),
            type=PermissionType.USER,
            role=role,
            email_address=email_address,
            display_name=None,
        )
        self._permissions[file_id].append(permission)
        return permission

    def revoke_permission(self, file_id: str, permission_id: str) -> None:
        if file_id not in self._permissions:
            raise FileNotFoundError(file_id)
        self._permissions[file_id] = [
            p for p in self._permissions[file_id] if p.id != permission_id
        ]

    def delete_file(self, file_id: str) -> None:
        if file_id not in self._files:
            raise FileNotFoundError(file_id)
        del self._files[file_id]
        self._file_bytes.pop(file_id, None)
        self._permissions.pop(file_id, None)

    def rename_file(self, file_id: str, new_name: str) -> DriveFile:
        if file_id not in self._files:
            raise FileNotFoundError(file_id)
        old = self._files[file_id]
        updated = DriveFile(
            id=old.id,
            name=new_name,
            mime_type=old.mime_type,
            size=old.size,
            parents=old.parents,
            created_time=old.created_time,
            modified_time=old.modified_time,
            web_view_link=old.web_view_link,
        )
        self._files[file_id] = updated
        return updated

    def make_anyone_with_link(self, file_id: str, role: str = "writer") -> None:
        pass  # 共有状態はテストで検証不要なので no-op

    def find_google_doc_by_name(
        self, name: str, parent_folder_id: str | None
    ) -> DriveFile | None:
        for f in self._files.values():
            if f.name == name and f.mime_type == "application/vnd.google-apps.document":
                if parent_folder_id is None or parent_folder_id in f.parents:
                    return f
        return None

    def upload_as_google_doc(
        self,
        docx_path: Path,
        title: str,
        parent_folder_id: str | None,
    ) -> DriveFile:
        new_id = str(uuid4())
        file = DriveFile(
            id=new_id,
            name=title,
            mime_type="application/vnd.google-apps.document",
            size=None,
            parents=(parent_folder_id,) if parent_folder_id else (),
            created_time=None,
            modified_time=None,
            web_view_link=f"https://docs.google.com/document/d/{new_id}/edit",
        )
        self._files[new_id] = file
        self._permissions[new_id] = []
        return file

    def update_google_doc_content(
        self,
        file_id: str,
        docx_path: Path,
        title: str,
    ) -> DriveFile:
        if file_id not in self._files:
            raise FileNotFoundError(file_id)
        old = self._files[file_id]
        updated = DriveFile(
            id=old.id,
            name=title,
            mime_type=old.mime_type,
            size=old.size,
            parents=old.parents,
            created_time=old.created_time,
            modified_time=old.modified_time,
            web_view_link=old.web_view_link,
        )
        self._files[file_id] = updated
        return updated

    def find_google_sheet_by_name(
        self, name: str, parent_folder_id: str | None
    ) -> DriveFile | None:
        for f in self._files.values():
            if f.name == name and f.mime_type == "application/vnd.google-apps.spreadsheet":
                if parent_folder_id is None or parent_folder_id in f.parents:
                    return f
        return None

    def upload_as_google_sheet(
        self,
        csv_path: Path,
        title: str,
        parent_folder_id: str | None,
    ) -> DriveFile:
        new_id = str(uuid4())
        file = DriveFile(
            id=new_id,
            name=title,
            mime_type="application/vnd.google-apps.spreadsheet",
            size=None,
            parents=(parent_folder_id,) if parent_folder_id else (),
            created_time=None,
            modified_time=None,
            web_view_link=f"https://docs.google.com/spreadsheets/d/{new_id}/edit",
        )
        self._files[new_id] = file
        self._permissions[new_id] = []
        return file

    def update_google_sheet_content(
        self,
        file_id: str,
        csv_path: Path,
        title: str,
    ) -> DriveFile:
        if file_id not in self._files:
            raise FileNotFoundError(file_id)
        old = self._files[file_id]
        updated = DriveFile(
            id=old.id,
            name=title,
            mime_type=old.mime_type,
            size=old.size,
            parents=old.parents,
            created_time=old.created_time,
            modified_time=old.modified_time,
            web_view_link=old.web_view_link,
        )
        self._files[file_id] = updated
        return updated

    def create_folder(self, name: str, parent_folder_id: str | None) -> DriveFile:
        new_id = str(uuid4())
        folder = DriveFile(
            id=new_id,
            name=name,
            mime_type="application/vnd.google-apps.folder",
            size=None,
            parents=(parent_folder_id,) if parent_folder_id else (),
            created_time=None,
            modified_time=None,
            web_view_link=None,
        )
        self._files[new_id] = folder
        self._permissions[new_id] = []
        return folder
