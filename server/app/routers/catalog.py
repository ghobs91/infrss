"""Primary-source catalog routes.

Two routers: ``public_router`` serves generated synthetic Atom feeds unauthenticated (the feed
refresh pipeline fetches them like any other feed), while ``router`` exposes authenticated
browsing and the subscribe-to-promote action.
"""

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_PAGE_SIZE
from app.core.custom_exceptions import NotFoundError
from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as catalog_feed_crud
from app.db.session import get_db, get_db_factory
from app.routers.feeds.feeds_subscription import resolve_target_folder
from app.services.catalog import synthetic
from app.services.catalog.promotion import subscribe_to_catalog_feed
from app.services.user.auth import get_current_user
from app.typing.catalog import CatalogFeedRead, PrimaryEntityRead
from app.typing.subscriptions import SubscriptionResponse
from app.typing.user import TokenData

logger = structlog.get_logger(__name__)

public_router = APIRouter(prefix="/catalog", tags=["Primary Catalog"])
router = APIRouter(prefix="/catalog", tags=["Primary Catalog"])


@public_router.get(
    "/synthetic/{feed_id}.atom",
    summary="Serve the generated Atom feed for a synthetic catalog source",
    response_class=Response,
    responses={
        200: {"content": {"application/atom+xml": {}}, "description": "Atom feed"},
        404: {"description": "Synthetic feed not available"},
    },
)
async def get_synthetic_feed(
    feed_id: UUID,
    db_factory: Annotated[Any, Depends(get_db_factory)],
) -> Response:
    """Return generated Atom for a synthetic newsroom source (unauthenticated by design)."""
    atom = await synthetic.render_synthetic_feed(db_factory, feed_id)
    if atom is None:
        raise NotFoundError(message="Synthetic feed not available")
    return Response(content=atom, media_type="application/atom+xml")


@router.get(
    "/entities",
    response_model=list[PrimaryEntityRead],
    summary="Browse primary entities",
)
async def list_entities(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> list[PrimaryEntityRead]:
    """List catalogued primary entities for browsing."""
    entities = await entity_crud.list_entities(db, limit=limit, offset=offset)
    return [PrimaryEntityRead.model_validate(entity, from_attributes=True) for entity in entities]


@router.get(
    "/feeds",
    response_model=list[CatalogFeedRead],
    summary="Browse catalog feeds",
)
async def list_catalog_feeds(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
    entity_id: UUID | None = Query(None, description="Restrict to one entity"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> list[CatalogFeedRead]:
    """List catalog feeds and their verification state."""
    feeds = await catalog_feed_crud.list_catalog_feeds(db, entity_id=entity_id, limit=limit, offset=offset)
    return [CatalogFeedRead.model_validate(feed, from_attributes=True) for feed in feeds]


@router.post(
    "/feeds/{feed_id}/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a catalog feed (promotes it into your feed library)",
)
async def subscribe_catalog_feed(
    feed_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    db_factory: Annotated[Any, Depends(get_db_factory)],
    current_user: Annotated[TokenData, Depends(get_current_user)],
    folder_id: UUID | str | None = Query(None),
) -> SubscriptionResponse:
    """Promote a catalog feed into the global feed table and subscribe the user."""
    user_uuid = UUID(current_user.sub)
    resolved_folder = await resolve_target_folder(db, user_uuid, folder_id)
    subscription, _ = await subscribe_to_catalog_feed(
        db_factory,
        user_id=user_uuid,
        catalog_feed_id=feed_id,
        folder_id=resolved_folder,
    )
    return subscription
