from pathlib import Path

import pytest

from google_drive_manager.application.use_cases import (
    CreateFolder,
    DeleteFile,
    ListFiles,
    UploadCsvAsGoogleSheet,
    UploadCsvAsGoogleSheetRequest,
    UploadMarkdownAsGoogleDoc,
    UploadMarkdownAsGoogleDocRequest,
    ListFilesRequest,
    ListPermissions,
    ReadFile,
    RenameFile,
    RevokePermission,
    ShareFile,
    ShareFileRequest,
    UploadFile,
    UploadFileRequest,
)
from google_drive_manager.domain.models import DriveFile, PermissionRole

from .fakes import FakeDrivePort, FakePandocConverter


def _file(
    id: str,
    name: str,
    mime: str = "text/markdown",
    parents: tuple[str, ...] = (),
) -> DriveFile:
    return DriveFile(
        id=id,
        name=name,
        mime_type=mime,
        size=0,
        parents=parents,
        created_time=None,
        modified_time=None,
        web_view_link=None,
    )


class TestListFiles:
    def test_returns_all_when_no_filter(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))
        drive.seed_file(_file("2", "b.csv", mime="text/csv"))

        result = ListFiles(drive).execute(ListFilesRequest())
        assert len(result) == 2

    def test_filters_by_mime_type(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))
        drive.seed_file(_file("2", "b.csv", mime="text/csv"))

        result = ListFiles(drive).execute(ListFilesRequest(mime_type="text/csv"))
        assert [f.id for f in result] == ["2"]

    def test_filters_by_folder_id(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md", parents=("folder-A",)))
        drive.seed_file(_file("2", "b.md", parents=("folder-B",)))

        result = ListFiles(drive).execute(ListFilesRequest(folder_id="folder-A"))
        assert [f.id for f in result] == ["1"]

    def test_respects_max_results_boundary(self):
        drive = FakeDrivePort()
        for i in range(5):
            drive.seed_file(_file(str(i), f"f{i}.md"))

        result = ListFiles(drive).execute(ListFilesRequest(max_results=2))
        assert len(result) == 2


class TestReadFile:
    def test_decodes_utf8_by_default(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"), content="hello 日本語".encode("utf-8"))

        assert ReadFile(drive).execute("1") == "hello 日本語"

    def test_returns_bytes_when_encoding_none(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.bin"), content=b"\x00\x01\x02")

        assert ReadFile(drive).execute("1", encoding=None) == b"\x00\x01\x02"

    def test_raises_when_file_missing(self):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            ReadFile(drive).execute("unknown")


class TestUploadFile:
    def test_uploads_existing_local_file(self, tmp_path: Path):
        local = tmp_path / "sample.md"
        local.write_text("content")
        drive = FakeDrivePort()

        result = UploadFile(drive).execute(
            UploadFileRequest(local_path=local, mime_type="text/markdown")
        )
        assert result.name == "sample.md"
        assert result.mime_type == "text/markdown"

    def test_raises_when_local_file_missing(self, tmp_path: Path):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            UploadFile(drive).execute(UploadFileRequest(local_path=tmp_path / "nope.md"))


class TestShareFile:
    def test_adds_permission_for_email(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))

        perm = ShareFile(drive).execute(
            ShareFileRequest(
                file_id="1",
                email_address="other@example.com",
                role=PermissionRole.READER,
            )
        )
        assert perm.email_address == "other@example.com"
        assert perm.role is PermissionRole.READER

    def test_persists_permission_for_listing(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))
        ShareFile(drive).execute(
            ShareFileRequest(
                file_id="1",
                email_address="o@example.com",
                role=PermissionRole.WRITER,
            )
        )
        perms = ListPermissions(drive).execute("1")
        assert len(perms) == 1
        assert perms[0].email_address == "o@example.com"


class TestUploadMarkdownAsGoogleDoc:
    def test_creates_new_google_doc(self, tmp_path: Path):
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        drive = FakeDrivePort()

        result = UploadMarkdownAsGoogleDoc(drive, FakePandocConverter()).execute(
            UploadMarkdownAsGoogleDocRequest(md_path=md)
        )
        assert result.name == "report"
        assert result.mime_type == "application/vnd.google-apps.document"

    def test_uses_doc_title_when_specified(self, tmp_path: Path):
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        drive = FakeDrivePort()

        result = UploadMarkdownAsGoogleDoc(drive, FakePandocConverter()).execute(
            UploadMarkdownAsGoogleDocRequest(md_path=md, doc_title="カスタムタイトル")
        )
        assert result.name == "カスタムタイトル"

    def test_updates_existing_doc_with_same_title(self, tmp_path: Path):
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        drive = FakeDrivePort()
        existing = drive.upload_as_google_doc(
            docx_path=tmp_path / "dummy.docx",
            title="report",
            parent_folder_id=None,
        )

        result = UploadMarkdownAsGoogleDoc(drive, FakePandocConverter()).execute(
            UploadMarkdownAsGoogleDocRequest(md_path=md)
        )
        assert result.id == existing.id
        assert result.name == "report"

    def test_aborts_when_pandoc_warns(self, tmp_path: Path):
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        drive = FakeDrivePort()

        with pytest.raises(RuntimeError, match="警告"):
            UploadMarkdownAsGoogleDoc(
                drive,
                FakePandocConverter(warnings=["[WARNING] Could not fetch resource images/a.png"]),
            ).execute(UploadMarkdownAsGoogleDocRequest(md_path=md))

    def test_raises_when_md_missing(self, tmp_path: Path):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            UploadMarkdownAsGoogleDoc(drive, FakePandocConverter()).execute(
                UploadMarkdownAsGoogleDocRequest(md_path=tmp_path / "none.md")
            )

    def test_propagates_pandoc_error(self, tmp_path: Path):
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        drive = FakeDrivePort()

        with pytest.raises(RuntimeError, match="変換失敗"):
            UploadMarkdownAsGoogleDoc(
                drive,
                FakePandocConverter(raise_error="pandoc 変換失敗:\nsome error"),
            ).execute(UploadMarkdownAsGoogleDocRequest(md_path=md))


class TestUploadCsvAsGoogleSheet:
    def test_creates_new_google_sheet(self, tmp_path: Path):
        csv = tmp_path / "data.csv"
        csv.write_text("a,b\n1,2\n")
        drive = FakeDrivePort()

        result = UploadCsvAsGoogleSheet(drive).execute(
            UploadCsvAsGoogleSheetRequest(csv_path=csv)
        )
        assert result.name == "data"
        assert result.mime_type == "application/vnd.google-apps.spreadsheet"

    def test_uses_sheet_title_when_specified(self, tmp_path: Path):
        csv = tmp_path / "data.csv"
        csv.write_text("a,b\n1,2\n")
        drive = FakeDrivePort()

        result = UploadCsvAsGoogleSheet(drive).execute(
            UploadCsvAsGoogleSheetRequest(csv_path=csv, sheet_title="カスタムシート")
        )
        assert result.name == "カスタムシート"

    def test_updates_existing_sheet_with_same_title(self, tmp_path: Path):
        csv = tmp_path / "data.csv"
        csv.write_text("a,b\n1,2\n")
        drive = FakeDrivePort()
        existing = drive.upload_as_google_sheet(
            csv_path=tmp_path / "dummy.csv",
            title="data",
            parent_folder_id=None,
        )

        result = UploadCsvAsGoogleSheet(drive).execute(
            UploadCsvAsGoogleSheetRequest(csv_path=csv)
        )
        assert result.id == existing.id
        assert result.name == "data"

    def test_raises_when_csv_missing(self, tmp_path: Path):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            UploadCsvAsGoogleSheet(drive).execute(
                UploadCsvAsGoogleSheetRequest(csv_path=tmp_path / "none.csv")
            )


class TestDeleteFile:
    def test_removes_file(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))

        DeleteFile(drive).execute("1")
        assert ListFiles(drive).execute(ListFilesRequest()) == []

    def test_raises_when_file_missing(self):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            DeleteFile(drive).execute("unknown")


class TestRenameFile:
    def test_renames_file(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "old.md"))

        updated = RenameFile(drive).execute("1", "new.md")
        assert updated.name == "new.md"
        assert updated.id == "1"

    def test_raises_when_file_missing(self):
        drive = FakeDrivePort()
        with pytest.raises(FileNotFoundError):
            RenameFile(drive).execute("unknown", "new.md")


class TestCreateFolder:
    def test_creates_folder_in_root(self):
        drive = FakeDrivePort()

        folder = CreateFolder(drive).execute(name="my-folder", parent_folder_id=None)
        assert folder.name == "my-folder"
        assert folder.mime_type == "application/vnd.google-apps.folder"
        assert folder.parents == ()

    def test_creates_folder_under_parent(self):
        drive = FakeDrivePort()

        folder = CreateFolder(drive).execute(name="sub", parent_folder_id="parent-id")
        assert "parent-id" in folder.parents


class TestRevokePermission:
    def test_removes_target_permission(self):
        drive = FakeDrivePort()
        drive.seed_file(_file("1", "a.md"))
        perm = ShareFile(drive).execute(
            ShareFileRequest(
                file_id="1",
                email_address="o@example.com",
                role=PermissionRole.READER,
            )
        )

        RevokePermission(drive).execute("1", perm.id)
        assert ListPermissions(drive).execute("1") == []
