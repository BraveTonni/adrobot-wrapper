"""Проверка наличия оффера перед изменением кампании."""

from app.application.errors import NotFoundError, RepositoryNotFoundError
from app.application.ports import OfferReader


async def ensure_offer_exists(client: OfferReader, offer_id: int) -> None:
    try:
        await client.get_offer(offer_id)
    except RepositoryNotFoundError as exc:
        raise NotFoundError(f"Оффер #{offer_id} не найден в Keitaro") from exc
