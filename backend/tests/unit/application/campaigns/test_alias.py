import re

from app.application.campaigns.alias import build_campaign_alias


def test_build_campaign_alias_transliterates_name_and_is_request_stable() -> (
    None
):
    first = build_campaign_alias("Летняя кампания / US", "request-123")

    assert re.fullmatch(r"letnyaya-kampaniya-us-[0-9a-f]{12}", first)
    assert build_campaign_alias("Летняя кампания / US", "request-123") == first
    assert build_campaign_alias("Летняя кампания / US", "request-456") != first


def test_build_campaign_alias_has_a_safe_fallback_for_non_latin_names() -> (
    None
):
    alias = build_campaign_alias("東京", "request-123")

    assert re.fullmatch(r"campaign-[0-9a-f]{12}", alias)
