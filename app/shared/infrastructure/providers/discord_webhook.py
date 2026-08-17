import json
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.modules.videos.domain.video import Video, VideoProcessingStatus
from config.settings import settings


class DiscordWebhookError(Exception):
    pass


@dataclass(frozen=True)
class DiscordWebhookResult:
    sent: bool
    reason: str | None = None


class DiscordWebhookNotifier:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        webhook_url: str | None = None,
        public_clip_base_url: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.enabled = settings.discord_webhook_enabled if enabled is None else enabled
        self.webhook_url = settings.discord_webhook_url if webhook_url is None else webhook_url
        self.public_clip_base_url = public_clip_base_url or _default_public_clip_base_url()
        self.timeout_seconds = timeout_seconds

    def notify_video_ready(self, video: Video) -> DiscordWebhookResult:
        if not self.enabled:
            return DiscordWebhookResult(sent=False, reason="disabled")
        if not self.webhook_url:
            return DiscordWebhookResult(sent=False, reason="missing_webhook_url")
        if not self.public_clip_base_url:
            return DiscordWebhookResult(sent=False, reason="missing_public_clip_base_url")
        if video.is_registered_only:
            return DiscordWebhookResult(sent=False, reason="registered_only")
        if video.processing_status != VideoProcessingStatus.READY:
            return DiscordWebhookResult(sent=False, reason="not_ready")

        payload = {
            "content": f"@{_video_username(video)}\n{self._clip_url(video)}",
            "allowed_mentions": {"parse": []},
        }
        self._post(payload)
        return DiscordWebhookResult(sent=True)

    def _clip_url(self, video: Video) -> str:
        return f"{self.public_clip_base_url.rstrip('/')}/clip/{video.id}/h264"

    def _post(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SpiderShare/discord-webhook",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status >= 400:
                    raise DiscordWebhookError(
                        f"Discord webhook returned HTTP {response.status}"
                    )
        except DiscordWebhookError:
            raise
        except Exception as error:
            raise DiscordWebhookError("Discord webhook request failed") from error


def _default_public_clip_base_url() -> str | None:
    base_url = settings.public_clip_base_url or settings.backoffice_api_base_url
    if not base_url:
        return None

    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return base_url


def _video_username(video: Video) -> str:
    if video.owner is None or not video.owner.username.strip():
        return "usuario"

    return video.owner.username.strip()
