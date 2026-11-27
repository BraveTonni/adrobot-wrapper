"""Проверка наличия оффера перед изменением кампании."""

from app.application.catalog.service import Catalog
from app.application.errors import NotFoundError, RepositoryNotFoundError
from app.application.ports import OfferReader


async def ensure_offer_exists(client: OfferReader, offer_id: int) -> None:
    try:
        await client.get_offer(offer_id)
    except RepositoryNotFoundError as exc:
        raise NotFoundError(f"Оффер #{offer_id} не найден в Keitaro") from exc


async def ensure_offer_in_catalog(
    catalog: Catalog | None, client: OfferReader, offer_id: int
) -> None:
    """Ищет оффер в кэше каталога, а без кэша — напрямую в Keitaro."""
    if catalog is None:
        await ensure_offer_exists(client, offer_id)
        return
    if not any(offer.id == offer_id for offer in await catalog.offers()):
        raise NotFoundError(f"Оффер #{offer_id} не найден в каталоге Keitaro")
