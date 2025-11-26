"""GraphQL enums and Strawberry types for heroes scope."""

from __future__ import annotations

import strawberry
from strawberry.experimental import pydantic as strawberry_pydantic

from app.enums import Locale
from app.heroes.enums import HeroKey
from app.heroes.models import Hero
from app.roles.enums import Role

LocaleEnum = strawberry.enum(Locale, name="Locale")
RoleEnum = strawberry.enum(Role, name="Role")
HeroKeyEnum = strawberry.enum(HeroKey, name="HeroKey")


@strawberry_pydantic.type(model=Hero, all_fields=True)
class HeroDetailsType:
    """Full hero payload, matching the REST `Hero` model."""


__all__ = [
    "HeroDetailsType",
    "HeroKeyEnum",
    "LocaleEnum",
    "RoleEnum",
]
