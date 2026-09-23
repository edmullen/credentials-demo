from app.outbound import resolve


def test_a_path_resolves_onto_the_providers_origin() -> None:
    resolved = resolve(
        "https://cred-demo-payroll.onrender.com",
        "/api/connections/requests/abc123/presentation",
    )
    assert resolved == "https://cred-demo-payroll.onrender.com/api/connections/requests/abc123/presentation"


def test_an_absolute_uri_on_another_origin_is_refused() -> None:
    resolved = resolve("https://cred-demo-payroll.onrender.com", "https://evil.example/steal")
    assert resolved is None


def test_a_different_scheme_is_refused() -> None:
    resolved = resolve("https://cred-demo-payroll.onrender.com", "http://cred-demo-payroll.onrender.com/x")
    assert resolved is None


def test_localhost_override_still_resolves_a_path() -> None:
    resolved = resolve("http://localhost:8002", "/api/connections/requests/x/presentation")
    assert resolved == "http://localhost:8002/api/connections/requests/x/presentation"
