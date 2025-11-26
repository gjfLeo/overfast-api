"""GraphQL context helpers."""

from dataclasses import dataclass

from fastapi import Request, Response

from app.config import settings


@dataclass(slots=True)
class GraphQLContext:
    """Context shared across GraphQL resolvers."""

    request: Request
    response: Response
    cache_ttl: int | None = None

    def merge_cache_ttl(self, ttl_header: str | None) -> None:
        """Keep the smallest cache TTL across all executed resolvers."""

        if ttl_header is None:
            return

        try:
            ttl_value = int(ttl_header)
        except (TypeError, ValueError):
            return

        if self.cache_ttl is None or ttl_value < self.cache_ttl:
            self.cache_ttl = ttl_value
            self.response.headers[settings.cache_ttl_header] = str(ttl_value)


async def build_context(request: Request, response: Response) -> GraphQLContext:
    """Context factory passed to Strawberry router."""

    return GraphQLContext(request=request, response=response)
