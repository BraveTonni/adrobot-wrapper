import pytest

from app.infrastructure.keitaro.errors import KeitaroError
from app.infrastructure.keitaro.response.parser import parse_list, parse_one


@pytest.mark.parametrize(
    "response",
    [
        [{"id": 1}],
        {"data": [{"id": 1}]},
        {"items": [{"id": 1}]},
        {"results": [{"id": 1}]},
    ],
)
def test_parse_list_extracts_supported_response_shapes(response) -> None:
    assert parse_list(response) == [{"id": 1}]


def test_parse_list_accepts_an_empty_list() -> None:
    assert parse_list([]) == []


@pytest.mark.parametrize("response", [None, "invalid", {"unknown": []}, [1]])
def test_parse_list_rejects_invalid_response_shapes(response) -> None:
    with pytest.raises(KeitaroError):
        parse_list(response)


@pytest.mark.parametrize("response", [{"id": 1}, [{"id": 1}]])
def test_parse_one_accepts_object_or_single_item_list(
    response: object,
) -> None:
    assert parse_one(response, "campaign") == {"id": 1}


def test_parse_one_rejects_response_without_id() -> None:
    with pytest.raises(KeitaroError, match="ID кампанию"):
        parse_one({"name": "missing id"}, "кампанию")
