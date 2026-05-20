import pytest

from app.shared.infrastructure.providers.steam.steam_client import SteamClient


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("76561198000000000", "76561198000000000"),
        (" alice ", "alice"),
        ("alice/", "alice"),
        ("https://steamcommunity.com/id/alice/", "alice"),
        ("https://steamcommunity.com/profiles/76561198000000000/", "76561198000000000"),
        ("https://steamcommunity.com/id/alice%20bob/", "alice bob"),
    ],
)
def test_normalize_steam_identifier(value: str, expected: str) -> None:
    steam_client = SteamClient(api_key="test-key")

    assert steam_client._normalize_steam_identifier(value) == expected


@pytest.mark.unit
def test_with_game_image_urls_adds_known_steam_image_urls() -> None:
    steam_client = SteamClient(api_key="test-key")

    result = steam_client._with_game_image_urls(
        {
            "appid": 10,
            "name": "Counter-Strike",
            "img_icon_url": "abc123",
        }
    )

    assert result["appid"] == 10
    assert result["name"] == "Counter-Strike"
    assert (
        result["icon_url"]
        == "https://media.steampowered.com/steamcommunity/public/images/apps/10/abc123.jpg"
    )
    assert result["header_image_url"] == (
        "https://cdn.akamai.steamstatic.com/steam/apps/10/header.jpg"
    )
    assert result["capsule_image_url"] == (
        "https://cdn.akamai.steamstatic.com/steam/apps/10/capsule_184x69.jpg"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("appid", "image_hash"),
    [
        (None, "abc123"),
        (10, None),
        (10, ""),
    ],
)
def test_community_app_image_url_returns_none_without_required_parts(
    appid: int | None,
    image_hash: str | None,
) -> None:
    steam_client = SteamClient(api_key="test-key")

    assert steam_client._community_app_image_url(appid, image_hash) is None


@pytest.mark.unit
def test_with_game_image_urls_returns_none_for_app_images_without_appid() -> None:
    steam_client = SteamClient(api_key="test-key")

    result = steam_client._with_game_image_urls({"name": "Unknown"})

    assert result["icon_url"] is None
    assert result["header_image_url"] is None
    assert result["capsule_image_url"] is None
