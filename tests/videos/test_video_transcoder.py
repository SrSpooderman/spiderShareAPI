import pytest

from app.modules.videos.domain.video import VideoAspectRatio
from app.shared.infrastructure.providers.storage.video_transcoder import (
    FfmpegVideoTranscoder,
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
