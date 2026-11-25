from app.transport.http.schemas.operations import OperationOut


def test_operation_schema_includes_public_audit_fields() -> None:
    response = OperationOut(
        id=1,
        created_at="2026-01-02T03:04:00+00:00",
        action="campaign.create",
        campaign_id=7,
        stream_id=None,
        status="ok",
        detail={"name": "x"},
    )

    assert response.model_dump()["action"] == "campaign.create"
    assert response.model_dump()["detail"] == {"name": "x"}
