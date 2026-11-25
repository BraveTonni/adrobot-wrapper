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
                actor=record.actor,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                before_payload=record.before_payload,
                after_payload=record.after_payload,
                error=record.error,
            )
            for record in records
        ]
