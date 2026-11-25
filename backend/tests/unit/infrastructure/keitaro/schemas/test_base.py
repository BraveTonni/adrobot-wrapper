from app.infrastructure.keitaro.schemas.base import KeitaroModel


def test_keitaro_model_ignores_unknown_fields_and_accepts_aliases() -> None:
    class Example(KeitaroModel):
        field_name: str

    model = Example.model_validate(
        {"field_name": "value", "unexpected": "ignored"}
    )

    assert model.field_name == "value"
    assert "unexpected" not in model.model_dump()
