import pytest

from app.domain.shares import distribute_shares


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, []),
        (-1, []),
        (1, [100]),
        (3, [34, 33, 33]),
        (6, [17, 17, 17, 17, 16, 16]),
        (100, [1] * 100),
    ],
)
def test_distributes_shares(count: int, expected: list[int]) -> None:
    assert distribute_shares(count) == expected


def test_rejects_more_than_one_hundred_offers() -> None:
    with pytest.raises(ValueError, match="100"):
        distribute_shares(101)
