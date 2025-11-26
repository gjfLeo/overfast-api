from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from fastapi import status

from app.heroes.enums import HeroKey
from app.roles.enums import Role

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _hero_short_payload(key: HeroKey, role: Role, portrait: str) -> dict:
    return {
        "key": key.value,
        "name": key.name.title(),
        "portrait": portrait,
        "role": role.value,
    }


def _hero_detail_payload(key: HeroKey, role: Role) -> dict:
    return {
        "name": key.name.title(),
        "description": "Support sniper",
        "portrait": f"https://example.com/{key.value}-detail.png",
        "role": role.value,
        "location": "Cairo, Egypt",
        "age": 60,
        "birthday": "1 Jan",
        "hitpoints": {
            "health": 200,
            "armor": 0,
            "shields": 0,
            "total": 200,
        },
        "abilities": [
            {
                "name": "Biotic Rifle",
                "description": "Shoots darts.",
                "icon": "https://example.com/biotic-rifle.png",
                "video": {
                    "thumbnail": "https://example.com/biotic-thumb.jpg",
                    "link": {
                        "mp4": "https://example.com/biotic.mp4",
                        "webm": "https://example.com/biotic.webm",
                    },
                },
            }
        ],
        "story": {
            "summary": "Ana supporting the overwatch taskforce.",
            "media": {
                "type": "video",
                "link": "https://youtu.be/example",
            },
            "chapters": [
                {
                    "title": "Origins",
                    "content": "Ana's origin story.",
                    "picture": "https://example.com/origins.jpg",
                }
            ],
        },
    }


def test_graphql_heroes_filter_by_keys_returns_details(client: "TestClient") -> None:
    query = """
        query Heroes($keys: [HeroKey!], $locale: Locale!) {
            heroes(keys: $keys, locale: $locale) {
                key
                name
                portrait
                details(locale: $locale) {
                    description
                    abilities {
                        name
                    }
                }
            }
        }
    """

    hero_short_payloads = [
        _hero_short_payload(HeroKey.ANA, Role.SUPPORT, "https://example.com/ana.png"),
        _hero_short_payload(
            HeroKey.SOJOURN,
            Role.DAMAGE,
            "https://example.com/sojourn.png",
        ),
    ]
    hero_detail = _hero_detail_payload(HeroKey.ANA, Role.SUPPORT)

    list_mock = AsyncMock(return_value=hero_short_payloads)
    detail_mock = AsyncMock(return_value=hero_detail)

    with (
        patch(
            "app.heroes.controllers.list_heroes_controller.ListHeroesController.process_request",
            list_mock,
        ),
        patch(
            "app.heroes.controllers.get_hero_controller.GetHeroController.process_request",
            detail_mock,
        ),
    ):
        response = client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"keys": ["ANA"], "locale": "ENGLISH_US"},
            },
        )

    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert "errors" not in payload
    assert len(payload["data"]["heroes"]) == 1
    hero = payload["data"]["heroes"][0]
    assert hero["key"] == "ANA"
    assert hero["details"]["abilities"][0]["name"] == "Biotic Rifle"
    list_mock.assert_awaited_once()
    detail_mock.assert_awaited_once()


def test_graphql_heroes_without_keys_returns_list(client: "TestClient") -> None:
    query = """
        query Heroes($role: Role, $locale: Locale!) {
            heroes(role: $role, locale: $locale) {
                key
                name
                role
            }
        }
    """
    hero_short_payloads = [
        _hero_short_payload(HeroKey.ANA, Role.SUPPORT, "https://example.com/ana.png"),
        _hero_short_payload(HeroKey.LUCIO, Role.SUPPORT, "https://example.com/lucio.png"),
    ]

    list_mock = AsyncMock(return_value=hero_short_payloads)
    detail_mock = AsyncMock()

    with (
        patch(
            "app.heroes.controllers.list_heroes_controller.ListHeroesController.process_request",
            list_mock,
        ),
        patch(
            "app.heroes.controllers.get_hero_controller.GetHeroController.process_request",
            detail_mock,
        ),
    ):
        response = client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"role": "SUPPORT", "locale": "ENGLISH_US"},
            },
        )

    payload = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert "errors" not in payload
    assert len(payload["data"]["heroes"]) == 2
    assert [hero["key"] for hero in payload["data"]["heroes"]] == ["ANA", "LUCIO"]
    detail_mock.assert_not_called()
