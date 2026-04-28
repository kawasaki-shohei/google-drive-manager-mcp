from unittest.mock import MagicMock, patch

import pytest


def _build_adapter_with_mocked_service(service_mock: MagicMock):
    """build() をモックして実 API 呼び出しなしで adapter を構築する。"""
    from google_drive_manager.adapters.google_drive_adapter import (
        GoogleDriveAdapter,
    )

    with patch(
        "google_drive_manager.adapters.google_drive_adapter.build",
        return_value=service_mock,
    ):
        return GoogleDriveAdapter(credentials=MagicMock())


class TestReadFileBytesMimeBranches:
    """read_file_bytes は mime_type に応じて取得方法を切り替える。

    Why: Google Docs / Sheets はバイナリ取得不可で export が必要 (Drive API 仕様)。
         通常ファイル (CSV / MD 等) は get_media で直接取得する。
    """

    def test_google_doc_uses_export_text_plain(self) -> None:
        files_mock = MagicMock()
        files_mock.get.return_value.execute.return_value = {
            "mimeType": "application/vnd.google-apps.document"
        }
        files_mock.export.return_value.execute.return_value = b"plain text body"
        service = MagicMock()
        service.files.return_value = files_mock

        adapter = _build_adapter_with_mocked_service(service)
        result = adapter.read_file_bytes("doc-id")

        assert result == b"plain text body"
        files_mock.export.assert_called_with(
            fileId="doc-id", mimeType="text/plain"
        )
        files_mock.get_media.assert_not_called()

    def test_google_sheet_uses_export_text_csv(self) -> None:
        files_mock = MagicMock()
        files_mock.get.return_value.execute.return_value = {
            "mimeType": "application/vnd.google-apps.spreadsheet"
        }
        files_mock.export.return_value.execute.return_value = b"col_a,col_b\n1,2\n"
        service = MagicMock()
        service.files.return_value = files_mock

        adapter = _build_adapter_with_mocked_service(service)
        result = adapter.read_file_bytes("sheet-id")

        assert result == b"col_a,col_b\n1,2\n"
        files_mock.export.assert_called_with(
            fileId="sheet-id", mimeType="text/csv"
        )
        files_mock.get_media.assert_not_called()

    def test_plain_file_uses_get_media(self, monkeypatch: pytest.MonkeyPatch) -> None:
        files_mock = MagicMock()
        files_mock.get.return_value.execute.return_value = {"mimeType": "text/csv"}
        request_mock = MagicMock()
        files_mock.get_media.return_value = request_mock
        service = MagicMock()
        service.files.return_value = files_mock

        # MediaIoBaseDownload は buffer に書き込む I/O 抽象。テストでは buffer に直接書く fake で差し替える。
        def fake_downloader(buffer, request):
            assert request is request_mock
            buffer.write(b"raw csv body")
            chunker = MagicMock()
            chunker.next_chunk.return_value = (None, True)
            return chunker

        monkeypatch.setattr(
            "google_drive_manager.adapters.google_drive_adapter.MediaIoBaseDownload",
            fake_downloader,
        )

        adapter = _build_adapter_with_mocked_service(service)
        result = adapter.read_file_bytes("plain-id")

        assert result == b"raw csv body"
        files_mock.get_media.assert_called_with(fileId="plain-id")
        files_mock.export.assert_not_called()