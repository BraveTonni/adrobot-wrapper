from app.domain.countries import is_country_code


def test_accepts_valid_alpha_two_country_code() -> None:
    assert is_country_code("US")


def test_rejects_invalid_and_lowercase_codes() -> None:
    assert not is_country_code("XX")
    assert not is_country_code("us")
    assert not is_country_code("USA")
