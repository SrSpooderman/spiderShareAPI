import json

import pytest

from app.modules.videos.domain.video import VideoProcessingStatus
from app.shared.infrastructure.providers.discord_webhook import DiscordWebhookNotifier


class FakeDiscordResponse:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


@pytest.mark.unit
def test_discord_webhook_skips_when_disabled(video_factory) -> None:
    notifier = DiscordWebhookNotifier(
        enabled=False,
        webhook_url="https://discord.example/webhook",
        public_clip_base_url="https://clips.example.com",
    )

    result = notifier.notify_video_ready(
        video_factory(processing_status=VideoProcessingStatus.READY)
    )

    assert result.sent is False
    assert result.reason == "disabled"


@pytest.mark.unit
def test_discord_webhook_skips_registered_only_video(video_factory) -> None:
    notifier = DiscordWebhookNotifier(
        enabled=True,
        webhook_url="https://discord.example/webhook",
        public_clip_base_url="https://clips.example.com",
    )

    result = notifier.notify_video_ready(
        video_factory(
            processing_status=VideoProcessingStatus.READY,
            is_registered_only=True,
        )
    )

    assert result.sent is False
    assert result.reason == "registered_only"


@pytest.mark.unit
def test_discord_webhook_posts_public_clip_url(monkeypatch, video_factory) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeDiscordResponse()

    monkeypatch.setattr(
        "app.shared.infrastructure.providers.discord_webhook.urlopen",
        fake_urlopen,
    )
    video = video_factory(
        title="Boss clip",
        description="Context",
        processing_status=VideoProcessingStatus.READY,
    )
    notifier = DiscordWebhookNotifier(
        enabled=True,
        webhook_url="https://discord.example/webhook",
        public_clip_base_url="https://clips.example.com/",
    )

    result = notifier.notify_video_ready(video)

    assert result.sent is True
    request, timeout = requests[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert timeout == 10
    assert request.full_url == "https://discord.example/webhook"
    assert payload["content"] == f"Nuevo clip: https://clips.example.com/clip/{video.id}"
    assert payload["embeds"][0]["url"] == f"https://clips.example.com/clip/{video.id}"


@pytest.mark.unit
def test_discord_webhook_uses_backoffice_api_base_url_by_default(
    monkeypatch,
    video_factory,
) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeDiscordResponse()

    monkeypatch.setattr(
        "app.shared.infrastructure.providers.discord_webhook.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "app.shared.infrastructure.providers.discord_webhook.settings.public_clip_base_url",
        None,
    )
    monkeypatch.setattr(
        "app.shared.infrastructure.providers.discord_webhook.settings.backoffice_api_base_url",
        "https://api.example.com",
    )
    video = video_factory(processing_status=VideoProcessingStatus.READY)
    notifier = DiscordWebhookNotifier(
        enabled=True,
        webhook_url="https://discord.example/webhook",
    )

    result = notifier.notify_video_ready(video)

    assert result.sent is True
    payload = json.loads(requests[0].data.decode("utf-8"))
    assert payload["content"] == f"Nuevo clip: https://api.example.com/clip/{video.id}"
