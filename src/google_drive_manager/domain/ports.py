from abc import ABC, abstractmethod
from pathlib import Path

from .models import DriveFile, Permission, PermissionRole


class PandocConverterPort(ABC):
    @abstractmethod
    def convert_md_to_docx(self, md_path: Path, output_path: Path) -> list[str]:
        """Convert Markdown to docx. Returns list of warning strings (empty if clean)."""
        ...


class DrivePort(ABC):
    @abstractmethod
    def list_files(
        self,
        folder_id: str | None,
        query: str | None,
        mime_type: str | None,
        max_results: int,
    ) -> list[DriveFile]: ...

    @abstractmethod
    def read_file_bytes(self, file_id: str) -> bytes: ...

    @abstractmethod
    def upload_file(
        self,
        local_path: Path,
        parent_folder_id: str | None,
        name: str | None,
        mime_type: str | None,
    ) -> DriveFile: ...

    @abstractmethod
    def list_permissions(self, file_id: str) -> list[Permission]: ...

    @abstractmethod
    def share_file(
        self,
        file_id: str,
        email_address: str,
        role: PermissionRole,
        notify: bool,
    ) -> Permission: ...

    @abstractmethod
    def revoke_permission(self, file_id: str, permission_id: str) -> None: ...

    @abstractmethod
    def create_folder(self, name: str, parent_folder_id: str | None) -> DriveFile: ...

    @abstractmethod
    def delete_file(self, file_id: str) -> None: ...

    @abstractmethod
    def rename_file(self, file_id: str, new_name: str) -> DriveFile: ...

    @abstractmethod
    def find_google_doc_by_name(
        self, name: str, parent_folder_id: str | None
    ) -> DriveFile | None: ...

    @abstractmethod
    def upload_as_google_doc(
        self,
        docx_path: Path,
        title: str,
        parent_folder_id: str | None,
    ) -> DriveFile: ...

    @abstractmethod
    def update_google_doc_content(
        self,
        file_id: str,
        docx_path: Path,
        title: str,
    ) -> DriveFile: ...

    @abstractmethod
    def find_google_sheet_by_name(
        self, name: str, parent_folder_id: str | None
    ) -> DriveFile | None: ...

    @abstractmethod
    def upload_as_google_sheet(
        self,
        csv_path: Path,
        title: str,
        parent_folder_id: str | None,
    ) -> DriveFile: ...

    @abstractmethod
    def update_google_sheet_content(
        self,
        file_id: str,
        csv_path: Path,
        title: str,
    ) -> DriveFile: ...

    @abstractmethod
    def make_anyone_with_link(self, file_id: str, role: str = "writer") -> None: ...
