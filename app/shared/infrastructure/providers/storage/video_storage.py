import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.modules.videos.application.errors import (
    VideoDurationTooLongError,
    VideoFileEmptyError,
    VideoFileTooLargeError,
    VideoUnsupportedMimeTypeError,
)
from app.modules.videos.domain.ports import VideoStorage
from app.modules.videos.domain.video import VideoVariantType
from config.settings import settings


class LocalVideoStorage(VideoStorage):
    chunk_size = 1024 * 1024

    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = Path(root_path or settings.video_storage_path)

    def save_original(
        self,
        *,
        video_id: UUID,
        original_filename: str,
        content_type: str | None,
        file: BinaryIO,
    ) -> None:
        self._validate_content_type(content_type)
        video_dir = self.root_path / "originals" / str(video_id)
        video_dir.mkdir(parents=True, exist_ok=True)
        target_path = video_dir / f"original{self._file_suffix(original_filename, content_type)}"

        bytes_written = 0
        try:
            with target_path.open("wb") as target:
                while chunk := file.read(self.chunk_size):
                    bytes_written += len(chunk)
                    if self._is_too_large(bytes_written):
                        raise VideoFileTooLargeError()
                    target.write(chunk)

            if bytes_written == 0:
                raise VideoFileEmptyError()

            self._validate_duration(target_path)
        except Exception:
            shutil.rmtree(video_dir, ignore_errors=True)
            raise

    def delete_original(self, video_id: UUID) -> None:
        shutil.rmtree(self.root_path / "originals" / str(video_id), ignore_errors=True)

    def delete_video_files(self, video_id: UUID) -> None:
        for folder in ("originals", "variants", "thumbnails"):
            path = self.root_path / folder / str(video_id)
            if path.exists():
                shutil.rmtree(path)

    def get_original_path(self, video_id: UUID) -> Path | None:
        original_dir = self.root_path / "originals" / str(video_id)
        return self._first_existing(original_dir.glob("original.*"))

    def get_variant_path(self, video_id: UUID, variant_type: VideoVariantType) -> Path | None:
        variant_path = self.root_path / "variants" / str(video_id) / f"{variant_type.value}.mp4"
        if variant_path.exists() and variant_path.is_file():
            return variant_path

        return None

    def get_thumbnail_path(self, video_id: UUID) -> Path | None:
        thumbnail_path = self.root_path / "thumbnails" / str(video_id) / "thumbnail.jpg"
        if thumbnail_path.exists() and thumbnail_path.is_file():
            return thumbnail_path

        return None

    def _validate_content_type(self, content_type: str | None) -> None:
        if content_type not in settings.video_allowed_mime_types:
            raise VideoUnsupportedMimeTypeError()

    def _is_too_large(self, bytes_written: int) -> bool:
        return (
            settings.max_video_size_bytes is not None
            and bytes_written > settings.max_video_size_bytes
        )

    def _validate_duration(self, path: Path) -> None:
        duration = self._probe_duration_seconds(path)
        if duration is None or settings.max_video_duration_seconds is None:
            return

        if duration > settings.max_video_duration_seconds:
            raise VideoDurationTooLongError()

    def _probe_duration_seconds(self, path: Path) -> float | None:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                check=True,
                text=True,
                timeout=15,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return None

        try:
            return float(result.stdout.strip())
        except ValueError:
            return None

    def _file_suffix(self, original_filename: str, content_type: str | None) -> str:
        suffix = Path(original_filename).suffix.lower()
        if suffix in {".mp4", ".webm"}:
            return suffix
        if content_type == "video/webm":
            return ".webm"

        return ".mp4"

    def _first_existing(self, paths) -> Path | None:
        for path in sorted(paths):
            if path.is_file():
                return path

        return None
