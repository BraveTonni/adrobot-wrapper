"""HTTP-контракт истории операций."""

from pydantic import BaseModel


class OperationOut(BaseModel):
    id: int
    created_at: str
    action: str
    campaign_id: int | None
    stream_id: int | None
    status: str
    detail: dict[str, object] | None
    actor: str
    entity_type: str
    entity_id: int | None
    before_payload: dict[str, object] | list[object] | None
    after_payload: dict[str, object] | list[object] | None
    error: str | None
