"""Коды стран ISO 3166-1 alpha-2."""

from functools import cache

import pycountry


@cache
def _codes() -> frozenset[str]:
    return frozenset(country.alpha_2 for country in pycountry.countries)


def is_country_code(code: str) -> bool:
    return code in _codes()
