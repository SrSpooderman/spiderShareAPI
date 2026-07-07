from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.videos.domain.video import VideoAspectRatio, VideoVariantType
from app.shared.infrastructure.providers.storage.video_transcoder import (
    FfmpegVideoTranscoder,
    _SourceMetadata,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("width", "height", "expected_width", "expected_height", "expected_ratio"),
    [
        (1920, 1080, 1920, 1080, VideoAspectRatio.RATIO_16_9),
        (1080, 1920, 2560, 1920, VideoAspectRatio.RATIO_4_3),
        (1000, 1000, 1334, 1000, VideoAspectRatio.RATIO_4_3),
        (3440, 1440, 3440, 1474, VideoAspectRatio.RATIO_21_9),
    ],
)
def test_transcoder_adapts_to_nearest_valid_ratio_without_cropping(
    width: int,
    height: int,
    expected_width: int,
    expected_height: int,
    expected_ratio: VideoAspectRatio,
) -> None:
    transcoder = FfmpegVideoTranscoder(root_path="/tmp/videos")

    geometry = transcoder._target_geometry(width, height)

    assert geometry.width == expected_width
    assert geometry.height == expected_height
    assert geometry.aspect_ratio == expected_ratio


@pytest.mark.unit
def test_transcoder_scale_filter_uses_padding_instead_of_crop() -> None:
    transcoder = FfmpegVideoTranscoder(root_path="/tmp/videos")
    geometry = transcoder._target_geometry(1080, 1920)

    scale_filter = transcoder._scale_pad_filter(geometry)

    assert "force_original_aspect_ratio=decrease" in scale_filter
    assert "pad=2560:1920:(ow-iw)/2:(oh-ih)/2" in scale_filter


@pytest.mark.unit
def test_transcoder_generates_only_low_h264_variant(tmp_path, monkeypatch) -> None:
    video_id = uuid4()
    source_path = tmp_path / "originals" / str(video_id) / "original.mp4"
    commands: list[list[str]] = []
    transcoder = FfmpegVideoTranscoder(root_path=str(tmp_path))

    def fake_probe_source(_video_id):
        return _SourceMetadata(
            path=source_path,
            width=1920,
            height=1080,
            duration_seconds=60.0,
            source_created_at=None,
        )

    def fake_run_ffmpeg(command: list[str]) -> None:
        commands.append(command)
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"output")

    monkeypatch.setattr(transcoder, "_probe_source", fake_probe_source)
    monkeypatch.setattr(transcoder, "_run_ffmpeg", fake_run_ffmpeg)

    result = transcoder.transcode(video_id)

    assert [variant.variant_type for variant in result.variants] == [
        VideoVariantType.LOW_H264,
    ]
    assert [variant.codec for variant in result.variants] == ["h264"]
    assert len(commands) == 2
    assert all("libaom-av1" not in command for command in commands)


@pytest.mark.unit
def test_transcoder_reads_source_creation_time_from_format_metadata() -> None:
    transcoder = FfmpegVideoTranscoder(root_path="/tmp/videos")

    source_created_at = transcoder._source_created_at(
        {
            "format": {
                "tags": {
                    "creation_time": "2026-07-07T18:22:10.000000Z",
                },
            },
            "streams": [],
        }
    )

    assert source_created_at == datetime(
        2026,
        7,
        7,
        18,
        22,
        10,
        tzinfo=timezone.utc,
    )
