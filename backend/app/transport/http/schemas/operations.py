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
    actor: str = "unknown"
    entity_type: str = "operation"
    entity_id: int | None = None
    before_payload: dict[str, object] | list[object] | None = None
    after_payload: dict[str, object] | list[object] | None = None
    error: str | None = None
