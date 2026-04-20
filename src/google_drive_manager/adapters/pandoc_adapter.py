import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from ..domain.ports import PandocConverterPort

_IMG_TAG_RE = re.compile(r'<img\s+src="([^"]+)"[^>]*>', re.IGNORECASE)
_MD_IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)', re.IGNORECASE)
_WEBP_SUFFIX = ".webp"


def _convert_webp_to_png(src: Path, dest_dir: Path) -> Path:
    png_path = dest_dir / (src.stem + ".png")
    with Image.open(src) as img:
        img.convert("RGBA").save(png_path, "PNG")
    return png_path


def _rewrite_img_paths(text: str, md_dir: Path, tmp_dir: Path) -> str:
    def replace(path_str: str) -> str:
        src = (md_dir / path_str).resolve()
        if src.suffix.lower() == _WEBP_SUFFIX and src.exists():
            return str(_convert_webp_to_png(src, tmp_dir))
        return str(src)

    text = _IMG_TAG_RE.sub(
        lambda m: f"![]({replace(m.group(1))})", text
    )
    text = _MD_IMG_RE.sub(
        lambda m: f"![{m.group(1)}]({replace(m.group(2))})", text
    )
    return text


class PandocAdapter(PandocConverterPort):
    def convert_md_to_docx(self, md_path: Path, output_path: Path) -> list[str]:
        pandoc_path = shutil.which("pandoc")
        if pandoc_path is None:
            raise FileNotFoundError(
                "pandoc コマンドが見つかりません。brew install pandoc で導入してください。"
            )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            normalized = _rewrite_img_paths(
                md_path.read_text(encoding="utf-8"),
                md_dir=md_path.parent,
                tmp_dir=tmp_dir,
            )
            tmp_md = tmp_dir / md_path.name
            tmp_md.write_text(normalized, encoding="utf-8")
            result = subprocess.run(
                [pandoc_path, str(tmp_md), "-o", str(output_path)],
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            raise RuntimeError(f"pandoc 変換失敗:\n{result.stderr}")
        return [line for line in result.stderr.splitlines() if "[WARNING]" in line]
