from app.providers import all_employers, all_providers, provider_for_employer


def test_fifteen_employers_with_display_fields() -> None:
    employers = all_employers()
    assert len(employers) == 15
    for e in employers:
        assert set(e) == {"id", "name", "industry", "city"}


def test_every_employer_under_exactly_one_provider() -> None:
    employers = {e["id"] for e in all_employers()}
    covered = [eid for p in all_providers().values() for eid in p["employers"]]
    assert sorted(covered) == sorted(employers)
    assert len(covered) == len(set(covered))


def test_provider_url_is_https() -> None:
    for provider in all_providers().values():
        assert provider["url"].startswith("https://")


def test_provider_for_employer() -> None:
    assert provider_for_employer("pinecrest") == "meridian"
    assert provider_for_employer("no-such-employer") is None


def test_meridian_url_override(monkeypatch) -> None:
    monkeypatch.setenv("MERIDIAN_PAYROLL_URL", "http://localhost:8002")
    from app.providers import all_providers as reload_providers

    reload_providers.cache_clear()
    try:
        assert all_providers()["meridian"]["url"] == "http://localhost:8002"
    finally:
        reload_providers.cache_clear()
