"""Представление истории операций в HTTP API."""

from app.domain.operations.entities import AuditRecord
from app.transport.http.schemas.operations import OperationOut


class OperationResponseFactory:
    @staticmethod
    def operations(records: list[AuditRecord]) -> list[OperationOut]:
        return [
            OperationOut(
                id=record.id,
                created_at=record.created_at.isoformat(),
                action=record.action,
                campaign_id=record.campaign_id,
                stream_id=record.stream_id,
                status=record.status,
                detail=record.detail,
            )
            for record in records
        ]
