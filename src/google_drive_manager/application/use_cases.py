import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..domain.models import DriveFile, Permission, PermissionRole
from ..domain.ports import DrivePort, PandocConverterPort


@dataclass(frozen=True)
class ListFilesRequest:
    folder_id: str | None = None
    query: str | None = None
    mime_type: str | None = None
    max_results: int = 100


class ListFiles:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, request: ListFilesRequest) -> list[DriveFile]:
        return self._drive.list_files(
            folder_id=request.folder_id,
            query=request.query,
            mime_type=request.mime_type,
            max_results=request.max_results,
        )


class ReadFile:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, file_id: str, encoding: str | None = "utf-8") -> str | bytes:
        data = self._drive.read_file_bytes(file_id)
        if encoding is None:
            return data
        return data.decode(encoding)


@dataclass(frozen=True)
class UploadFileRequest:
    local_path: Path
    parent_folder_id: str | None = None
    name: str | None = None
    mime_type: str | None = None


class UploadFile:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, request: UploadFileRequest) -> DriveFile:
        if not request.local_path.exists():
            raise FileNotFoundError(f"Local file not found: {request.local_path}")
        return self._drive.upload_file(
            local_path=request.local_path,
            parent_folder_id=request.parent_folder_id,
            name=request.name,
            mime_type=request.mime_type,
        )


class ListPermissions:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, file_id: str) -> list[Permission]:
        return self._drive.list_permissions(file_id)


@dataclass(frozen=True)
class ShareFileRequest:
    file_id: str
    email_address: str
    role: PermissionRole
    notify: bool = False


class ShareFile:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, request: ShareFileRequest) -> Permission:
        return self._drive.share_file(
            file_id=request.file_id,
            email_address=request.email_address,
            role=request.role,
            notify=request.notify,
        )


class RevokePermission:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, file_id: str, permission_id: str) -> None:
        self._drive.revoke_permission(file_id, permission_id)


class DeleteFile:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, file_id: str) -> None:
        self._drive.delete_file(file_id)


class RenameFile:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, file_id: str, new_name: str) -> DriveFile:
        return self._drive.rename_file(file_id=file_id, new_name=new_name)


@dataclass(frozen=True)
class UploadMarkdownAsGoogleDocRequest:
    md_path: Path
    drive_folder_id: str | None = None
    doc_title: str | None = None


class UploadMarkdownAsGoogleDoc:
    def __init__(self, drive: DrivePort, converter: PandocConverterPort) -> None:
        self._drive = drive
        self._converter = converter

    def execute(self, request: UploadMarkdownAsGoogleDocRequest) -> DriveFile:
        if not request.md_path.exists():
            raise FileNotFoundError(f"Markdown ファイルが見つかりません: {request.md_path}")
        title = request.doc_title or request.md_path.stem
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = Path(tmpdir) / f"{title}.docx"
            warnings = self._converter.convert_md_to_docx(
                md_path=request.md_path,
                output_path=docx_path,
            )
            if warnings:
                raise RuntimeError(
                    "pandoc 変換に警告が発生したためアップロードを中断しました。\n"
                    + "\n".join(warnings)
                )
            existing = self._drive.find_google_doc_by_name(
                name=title,
                parent_folder_id=request.drive_folder_id,
            )
            if existing:
                result = self._drive.update_google_doc_content(
                    file_id=existing.id,
                    docx_path=docx_path,
                    title=title,
                )
            else:
                result = self._drive.upload_as_google_doc(
                    docx_path=docx_path,
                    title=title,
                    parent_folder_id=request.drive_folder_id,
                )
            self._drive.make_anyone_with_link(result.id)
            return result


@dataclass(frozen=True)
class UploadCsvAsGoogleSheetRequest:
    csv_path: Path
    drive_folder_id: str | None = None
    sheet_title: str | None = None


class UploadCsvAsGoogleSheet:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, request: UploadCsvAsGoogleSheetRequest) -> DriveFile:
        if not request.csv_path.exists():
            raise FileNotFoundError(f"CSV ファイルが見つかりません: {request.csv_path}")
        title = request.sheet_title or request.csv_path.stem
        existing = self._drive.find_google_sheet_by_name(
            name=title,
            parent_folder_id=request.drive_folder_id,
        )
        if existing:
            result = self._drive.update_google_sheet_content(
                file_id=existing.id,
                csv_path=request.csv_path,
                title=title,
            )
        else:
            result = self._drive.upload_as_google_sheet(
                csv_path=request.csv_path,
                title=title,
                parent_folder_id=request.drive_folder_id,
            )
        self._drive.make_anyone_with_link(result.id)
        return result


class CreateFolder:
    def __init__(self, drive: DrivePort) -> None:
        self._drive = drive

    def execute(self, name: str, parent_folder_id: str | None) -> DriveFile:
        return self._drive.create_folder(name=name, parent_folder_id=parent_folder_id)
