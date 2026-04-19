import shutil
import subprocess
from pathlib import Path

from ..domain.ports import PandocConverterPort


class PandocAdapter(PandocConverterPort):
    def convert_md_to_docx(self, md_path: Path, output_path: Path) -> list[str]:
        pandoc_path = shutil.which("pandoc")
        if pandoc_path is None:
            raise FileNotFoundError(
                "pandoc コマンドが見つかりません。brew install pandoc で導入してください。"
            )
        result = subprocess.run(
            [
                pandoc_path,
                str(md_path),
                "-o", str(output_path),
                "--resource-path", str(md_path.parent),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pandoc 変換失敗:\n{result.stderr}")
        return [line for line in result.stderr.splitlines() if "[WARNING]" in line]
