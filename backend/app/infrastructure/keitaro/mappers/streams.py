"""Преобразование потоков между доменом и Keitaro API."""

from typing import Any

from app.domain.campaigns.entities import Stream, StreamOffer
from app.infrastructure.keitaro.schemas import (
    Stream as KeitaroStream,
)
from app.infrastructure.keitaro.schemas import (
    StreamOffer as KeitaroStreamOffer,
)

READ_ONLY_OFFER_FIELDS = frozenset(
    {"id", "stream_id", "created_at", "updated_at"}
)


def stream_to_domain(stream: KeitaroStream) -> Stream:
    return Stream(
        id=stream.id,
        campaign_id=stream.campaign_id,
        name=stream.name,
        type=stream.type,
        schema=stream.schema_,
        position=stream.position,
        state=stream.state,
        offers=[stream_offer_to_domain(offer) for offer in stream.offers],
        raw_payload=stream.model_dump(by_alias=True, exclude_unset=True),
    )


def stream_offer_to_domain(offer: KeitaroStreamOffer) -> StreamOffer:
    data = offer.model_dump(exclude_none=True)
    metadata = {
        key: value
        for key, value in data.items()
        if key not in {"offer_id", "share", "state"}
        and key != "is_pinned"
        and key not in READ_ONLY_OFFER_FIELDS
    }
    return StreamOffer(
        offer_id=offer.offer_id,
        share=offer.share,
        state=offer.state,
        metadata=metadata,
        is_pinned=bool(data.get("is_pinned", False)),
    )


def stream_offer_to_keitaro(offer: StreamOffer) -> dict[str, Any]:
    data = {
        key: value
        for key, value in offer.metadata.items()
        if key not in READ_ONLY_OFFER_FIELDS
    }
    data["offer_id"] = offer.offer_id
    data["share"] = offer.share
    if offer.state is not None:
        data["state"] = offer.state
    if offer.is_pinned:
        data["is_pinned"] = True
    return data
