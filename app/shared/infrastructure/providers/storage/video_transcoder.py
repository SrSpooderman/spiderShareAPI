import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.modules.videos.domain.ports import VideoTranscoder
from app.modules.videos.domain.video import (
    VideoAspectRatio,
    VideoProcessingResult,
    VideoVariantCreate,
    VideoVariantType,
)
from config.settings import settings


@dataclass(frozen=True)
class _SourceMetadata:
    path: Path
    width: int
    height: int
    video_codec: str
    duration_seconds: float
    source_created_at: datetime | None


@dataclass(frozen=True)
class _OutputGeometry:
    width: int
    height: int
    aspect_ratio: VideoAspectRatio


class FfmpegVideoTranscoder(VideoTranscoder):
    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = Path(root_path or settings.video_storage_path)

    def transcode(self, video_id: UUID) -> VideoProcessingResult:
        source = self._probe_source(video_id)
        original_geometry = self._target_geometry(source.width, source.height)
        low_geometry = self._low_geometry(original_geometry)
        variants_dir = self.root_path / "variants" / str(video_id)
        thumbnails_dir = self.root_path / "thumbnails" / str(video_id)
        tmp_dir = self.root_path / "processing_tmp" / str(video_id)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        variants_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        original_h264_path = variants_dir / "original_h264.mp4"
        h264_path = variants_dir / "low_h264.mp4"
        thumbnail_path = thumbnails_dir / "thumbnail.jpg"
        tmp_original_h264_path = tmp_dir / "original_h264.mp4"
        tmp_h264_path = tmp_dir / "low_h264.mp4"
        tmp_thumbnail_path = tmp_dir / "thumbnail.jpg"

        try:
            if self._is_av1(source):
                self._run_ffmpeg(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(source.path),
                        "-vf",
                        self._scale_pad_filter(original_geometry),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "20",
                        "-c:a",
                        "aac",
                        "-movflags",
                        "+faststart",
                        str(tmp_original_h264_path),
                    ]
                )
            self._run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source.path),
                    "-vf",
                    self._scale_pad_filter(low_geometry),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    str(tmp_h264_path),
                ]
            )
            self._run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source.path),
                    "-ss",
                    "00:00:01",
                    "-frames:v",
                    "1",
                    "-vf",
                    self._scale_pad_filter(low_geometry),
                    str(tmp_thumbnail_path),
                ]
            )
            if tmp_original_h264_path.exists():
                tmp_original_h264_path.replace(original_h264_path)
            tmp_h264_path.replace(h264_path)
            tmp_thumbnail_path.replace(thumbnail_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        variants = []
        if original_h264_path.exists():
            variants.append(
                self._variant(
                    video_id=video_id,
                    variant_type=VideoVariantType.ORIGINAL_H264,
                    codec="h264",
                    path=original_h264_path,
                    geometry=original_geometry,
                )
            )
        variants.append(
            self._variant(
                video_id=video_id,
                variant_type=VideoVariantType.LOW_H264,
                codec="h264",
                path=h264_path,
                geometry=low_geometry,
            )
        )

        return VideoProcessingResult(
            width=original_geometry.width,
            height=original_geometry.height,
            aspect_ratio=original_geometry.aspect_ratio,
            duration_seconds=source.duration_seconds,
            source_created_at=source.source_created_at,
            thumbnail_path=self._relative_path(thumbnail_path),
            variants=variants,
        )

    def _probe_source(self, video_id: UUID) -> _SourceMetadata:
        original_dir = self.root_path / "originals" / str(video_id)
        candidates = sorted(original_dir.glob("original.*"))
        if not candidates:
            raise FileNotFoundError(f"Original video not found for {video_id}")

        path = candidates[0]
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                (
                    "stream=width,height:stream_tags=creation_time:"
                    "format=duration:format_tags=creation_time"
                ),
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        metadata = json.loads(result.stdout)
        stream = metadata["streams"][0]

        return _SourceMetadata(
            path=path,
            width=int(stream["width"]),
            video_codec=str(stream.get("codec_name") or "").lower(),
            height=int(stream["height"]),
            duration_seconds=float(metadata["format"]["duration"]),
            source_created_at=self._source_created_at(metadata),
        )

    def _is_av1(self, source: _SourceMetadata) -> bool:
        return source.video_codec == "av1"

    def _source_created_at(self, metadata: dict) -> datetime | None:
        candidates = [
            metadata.get("format", {}).get("tags", {}).get("creation_time"),
            *[
                stream.get("tags", {}).get("creation_time")
                for stream in metadata.get("streams", [])
            ],
        ]
        for value in candidates:
            if not value:
                continue
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue

        return None

    def _target_geometry(self, width: int, height: int) -> _OutputGeometry:
        source_ratio = width / height
        ratios = {
            VideoAspectRatio.RATIO_4_3: 4 / 3,
            VideoAspectRatio.RATIO_16_9: 16 / 9,
            VideoAspectRatio.RATIO_21_9: 21 / 9,
        }
        aspect_ratio, target_ratio = min(
            ratios.items(),
            key=lambda item: abs(source_ratio - item[1]),
        )

        if source_ratio > target_ratio:
            output_width = self._even(width)
            output_height = self._even(round(output_width / target_ratio))
        else:
            output_height = self._even(height)
            output_width = self._even(round(output_height * target_ratio))

        return _OutputGeometry(output_width, output_height, aspect_ratio)

    def _low_geometry(self, geometry: _OutputGeometry) -> _OutputGeometry:
        if geometry.height <= 720:
            return geometry

        ratio = geometry.width / geometry.height
        height = 720
        width = self._even(round(height * ratio))

        return _OutputGeometry(width, height, geometry.aspect_ratio)

    def _scale_pad_filter(self, geometry: _OutputGeometry) -> str:
        return (
            f"scale={geometry.width}:{geometry.height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={geometry.width}:{geometry.height}:(ow-iw)/2:(oh-ih)/2"
        )

    def _variant(
        self,
        *,
        video_id: UUID,
        variant_type: VideoVariantType,
        codec: str,
        path: Path,
        geometry: _OutputGeometry,
    ) -> VideoVariantCreate:
        return VideoVariantCreate(
            variant_type=variant_type,
            codec=codec,
            container="mp4",
            width=geometry.width,
            height=geometry.height,
            bitrate_kbps=None,
            size_bytes=path.stat().st_size,
            path=self._relative_path(path),
        )

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.root_path).as_posix()

    def _run_ffmpeg(self, command: list[str]) -> None:
        subprocess.run(command, capture_output=True, check=True, text=True)

    def _even(self, value: int) -> int:
        return max(2, value if value % 2 == 0 else value + 1)
