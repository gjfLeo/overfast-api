"""Strawberry schema exposing the heroes scope."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import strawberry
from fastapi import Response
from strawberry import Private
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app.config import settings
from app.enums import Locale
from app.graphql.context import GraphQLContext, build_context
from app.graphql.types import HeroDetailsType, HeroKeyEnum, LocaleEnum, RoleEnum
from app.heroes.controllers.get_hero_controller import GetHeroController
from app.heroes.controllers.list_heroes_controller import ListHeroesController
from app.heroes.enums import HeroKey
from app.heroes.models import Hero, HeroShort
from app.roles.enums import Role



def _convert_role(role: RoleEnum | None) -> Role | None:
    if role is None:
        return None
    if isinstance(role.value, Role):
        return role.value
    return Role(role.value)


def _convert_locale(locale: LocaleEnum) -> Locale:
    if isinstance(locale.value, Locale):
        return locale.value
    return Locale(locale.value)


def _convert_keys(keys: Iterable[HeroKeyEnum]) -> list[HeroKey]:
    return [_enum_to_hero_key(key) for key in keys]


def _enum_to_hero_key(enum_member: HeroKeyEnum) -> HeroKey:
    if isinstance(enum_member.value, HeroKey):
        return enum_member.value
    return HeroKey(enum_member.value)


def _hero_key_to_enum(hero_key: HeroKey) -> HeroKeyEnum:
    try:
        return HeroKeyEnum(hero_key)
    except ValueError:
        return HeroKeyEnum(hero_key.value)


def _role_to_enum(role: Role) -> RoleEnum:
    try:
        return RoleEnum(role)
    except ValueError:
        return RoleEnum(role.value)


async def _run_controller(
    info: Info[GraphQLContext, Any],
    controller_cls: type,
    **kwargs: Any,
) -> Any:
    temp_response = Response()
    controller = controller_cls(info.context.request, temp_response)
    payload = await controller.process_request(**kwargs)
    info.context.merge_cache_ttl(
        temp_response.headers.get(settings.cache_ttl_header),
    )
    return payload


def _parse_models(
    model_cls: type[HeroShort],
    data: Iterable[Any],
) -> list[HeroShort]:
    return [model_cls.model_validate(item) for item in data]


@dataclass
class HeroNode:
    key: HeroKeyEnum
    name: str
    portrait: str
    role: RoleEnum
    _details_cache: Private[dict[str, Hero]] = field(default_factory=dict)

    async def _load_details(
        self,
        info: Info[GraphQLContext, Any],
        locale: LocaleEnum,
    ) -> Hero:
        cache_key = locale.value
        if cached := self._details_cache.get(cache_key):
            return cached

        payload = await _run_controller(
            info,
            GetHeroController,
            hero_key=_enum_to_hero_key(self.key),
            locale=_convert_locale(locale),
        )
        hero = Hero.model_validate(payload)
        self._details_cache[cache_key] = hero
        return hero

    @strawberry.field(description="Full hero payload, fetched on demand.")
    async def details(
        self,
        info: Info[GraphQLContext, Any],
        locale: LocaleEnum = LocaleEnum.ENGLISH_US,
    ) -> HeroDetailsType:
        hero = await self._load_details(info, locale)
        return HeroDetailsType.from_pydantic(hero)


def _make_hero_node(hero_short: HeroShort) -> HeroNode:
    return HeroNode(
        key=_hero_key_to_enum(hero_short.key),
        name=hero_short.name,
        portrait=str(hero_short.portrait),
        role=_role_to_enum(hero_short.role),
    )


def _filter_by_keys(
    hero_shorts: Iterable[HeroShort],
    keys: list[HeroKey],
) -> list[HeroShort]:
    if not keys:
        return list(hero_shorts)

    by_key = {hero.key: hero for hero in hero_shorts}
    filtered: list[HeroShort] = []
    for key in keys:
        if hero := by_key.get(key):
            filtered.append(hero)
    return filtered


@strawberry.type
class Query:
    @strawberry.field(description="List heroes, optionally filtering by role or key.")
    async def heroes(
        self,
        info: Info[GraphQLContext, Any],
        role: RoleEnum | None = None,
        locale: LocaleEnum = LocaleEnum.ENGLISH_US,
        keys: list[HeroKeyEnum] | None = None,
    ) -> list[HeroNode]:
        payload = await _run_controller(
            info,
            ListHeroesController,
            role=_convert_role(role),
            locale=_convert_locale(locale),
        )
        hero_shorts = _parse_models(HeroShort, payload)
        hero_keys = _convert_keys(keys) if keys else []
        filtered = _filter_by_keys(hero_shorts, hero_keys)
        return [_make_hero_node(hero) for hero in filtered]


schema = strawberry.Schema(Query)
graphql_router = GraphQLRouter(
    schema,
    context_getter=build_context,
)
