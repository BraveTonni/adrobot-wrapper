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
