"""Income on the Credentials page: the stack, the issuer color, New, and the income pages
(docs/design.md §8)."""

import json
import uuid
from datetime import UTC, datetime

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

from app import clock, credentials, state
from app.main import app

client = TestClient(app)

ISSUER_ID = "https://cred-demo-payroll.onrender.com"
SUBJECT_ID = "urn:uuid:22222222-2222-5222-8222-222222222222"


def _payroll_key() -> tuple[object, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
    public["kid"] = "payroll-1"
    return key, public


@pytest.fixture
def payroll_trust(monkeypatch):
    """Real committed identity credentials, plus a throwaway Payroll key trusted for
    PaystubCredential only — so income credentials in these tests genuinely verify."""
    key, public = _payroll_key()
    stored, _ = credentials._committed()
    trust = {ISSUER_ID: {"name": "Meridian Payroll", "trustedFor": ["PaystubCredential"], "keys": [public]}}
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))
    return key


def _income(
    key, *, n=1, employer="Pinecrest Home Care", hue="255",
    pay_period_start="2026-09-01", pay_period_end="2026-09-15", pay_date="2026-09-15",
    gross=1100.0, net=955.87, tamper=False,
) -> tuple[str, str]:
    """Returns (credential_id, jwt)."""
    credential_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'test-paystub-{n}')}"
    color = f"oklch(0.46 0.11 {hue})" if hue else None
    payload = {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id,
        "type": ["VerifiableCredential", "PaystubCredential"],
        "issuer": {"id": ISSUER_ID, "name": "Meridian Payroll"},
        "validFrom": f"{pay_date}T00:00:00Z",
        "credentialSubject": {
            "id": SUBJECT_ID,
            "employer": {"type": "Organization", "name": employer},
            "payPeriodStart": pay_period_start,
            "payPeriodEnd": pay_period_end,
            "payDate": pay_date,
            "payFrequency": "semimonthly",
            "grossPay": {"type": "MonetaryAmount", "value": gross, "currency": "USD"},
            "netPay": {"type": "MonetaryAmount", "value": net, "currency": "USD"},
        },
    }
    if color:
        payload["renderMethod"] = [{"type": "CredDemoIssuerColor", "color": color}]
    token = jwt.encode(payload, key, algorithm="ES256", headers={"kid": "payroll-1", "typ": "vc+jwt"})
    if tamper:
        header, body, sig = token.split(".")
        claims = json.loads(jwt.utils.base64url_decode(body + "=" * (-len(body) % 4)))
        claims["credentialSubject"]["grossPay"]["value"] = 99999.0
        body = jwt.utils.base64url_encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
        token = ".".join([header, body, sig])
    return credential_id, token


def _receive(person_id: str, *tokens: tuple[str, str]) -> None:
    for credential_id, token in tokens:
        state.add_received(person_id, credential_id, token)


def test_one_held_is_a_full_card_not_a_stack(payroll_trust) -> None:
    _receive("p01", _income(payroll_trust, n=1))
    body = client.get("/p/p01/credentials").text
    assert "1 credential" in body
    assert 'class="stack-cards"' not in body
    assert 'class="cred cred--income cred--issuer"' in body
    assert 'style="--issuer-hue: 255"' in body
    assert "Pinecrest Home Care" in body
    assert "$1,100.00" in body


def test_two_to_five_draw_as_a_stack_with_n_and_i(payroll_trust) -> None:
    tokens = [_income(payroll_trust, n=i, pay_date=f"2026-09-{10+i:02d}") for i in range(2)]
    _receive("p01", *tokens)
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards" style="--n: 1"' in body
    assert body.count('class="stack-cards__card cred--issuer"') == 2
    assert 'style="--i: 0; --issuer-hue: 255"' in body
    assert 'style="--i: 1; --issuer-hue: 255"' in body
    assert "stack-cards__more" not in body


def test_more_than_five_draws_five_plus_the_ledge(payroll_trust) -> None:
    tokens = [_income(payroll_trust, n=i, pay_date=f"2026-09-{10+i:02d}") for i in range(6)]
    _receive("p01", *tokens)
    body = client.get("/p/p01/credentials").text
    assert 'class="stack-cards" style="--n: 5"' in body
    assert body.count('class="stack-cards__card cred--issuer"') == 5
    assert '<a class="stack-cards__more" href="/p/p01/credentials/income" style="--i: 0">View all Income credentials (6)</a>' in body
    assert "6 credentials" in body


def test_ledge_never_gets_the_issuer_class(payroll_trust) -> None:
    tokens = [_income(payroll_trust, n=i, pay_date=f"2026-09-{10+i:02d}") for i in range(6)]
    _receive("p01", *tokens)
    body = client.get("/p/p01/credentials").text
    ledge = body[body.index('class="stack-cards__more"') - 40 : body.index('class="stack-cards__more"') + 120]
    assert "cred--issuer" not in ledge


def test_unreadable_or_missing_hue_falls_back_to_no_issuer_class(payroll_trust) -> None:
    _receive("p01", _income(payroll_trust, n=1, hue=None))
    body = client.get("/p/p01/credentials").text
    assert 'class="cred cred--income"' in body
    assert "cred--issuer" not in body


def test_tampered_card_gets_no_hue_either(payroll_trust) -> None:
    _receive("p01", _income(payroll_trust, n=1, tamper=True))
    body = client.get("/p/p01/credentials").text
    assert 'class="cred cred--income"' in body
    assert "cred--issuer" not in body
    assert ">Tampered<" in body


def test_new_pill_shows_once_then_is_gone(payroll_trust) -> None:
    _receive("p01", _income(payroll_trust, n=1))
    first = client.get("/p/p01/credentials").text
    assert 'class="cred__new">New</span>' in first
    assert "1 credential · 1 new" in first.replace("&middot;", "·")
    second = client.get("/p/p01/credentials").text
    assert 'class="cred__new">New</span>' not in second
    assert "· 1 new" not in second.replace("&middot;", "·")


def test_income_credential_id_isnt_read_as_a_credential_id() -> None:
    # /credentials/income must resolve to the list page, not a 404 lookup for id "income".
    response = client.get("/p/p01/credentials/income")
    assert response.status_code == 200
    assert "Income credentials" in response.text


def test_income_list_page_shows_every_held_credential_newest_first(payroll_trust) -> None:
    older, newer = (
        _income(payroll_trust, n=1, pay_date="2026-09-15"),
        _income(payroll_trust, n=2, pay_date="2026-09-30"),
    )
    # A real fetch inserts in Payroll's order, newest first (docs/design.md §4, §7).
    _receive("p01", newer, older)
    body = client.get("/p/p01/credentials/income").text
    assert body.index(newer[0].removeprefix("urn:uuid:")) < body.index(older[0].removeprefix("urn:uuid:"))
    assert "2 credentials" in body


def test_income_detail_page_shows_valid_from_and_doesnt_expire(payroll_trust) -> None:
    credential_id, token = _income(payroll_trust, n=1)
    _receive("p01", (credential_id, token))
    view_id = credential_id.removeprefix("urn:uuid:")
    body = client.get(f"/p/p01/credentials/{view_id}").text
    assert "Income credential" in body
    assert "Valid from 15 September 2026" in body
    assert "Doesn&rsquo;t expire" in body
    assert "(no validUntil)" in body


def test_income_detail_tampered_variant_shows_the_note(payroll_trust) -> None:
    credential_id, token = _income(payroll_trust, n=1, tamper=True)
    _receive("p01", (credential_id, token))
    view_id = credential_id.removeprefix("urn:uuid:")
    body = client.get(f"/p/p01/credentials/{view_id}").text
    assert ">Tampered<" in body
    assert "The rest of this credential is shown as it was received." in body
    assert 'cred--issuer' in body  # the issuer bar still colors on the detail page, per the handoff


# ---- The check state below the cards (docs/design.md §9) ---------------------------------------


def _connect(person_id: str) -> None:
    link = state.add_employer(person_id, "meridian", "pinecrest")
    link.connected_at = clock.now()
    link.connection_id = "conn-1"


def test_finished_with_new_cards_shows_neither_form_nor_error(payroll_trust) -> None:
    _connect("p01")
    state.set_check(
        "p01", "meridian",
        state.Check(state="done", token="t", result="new", count=1, finished_at=clock.now()),
    )
    _receive("p01", _income(payroll_trust, n=1))
    body = client.get("/p/p01/credentials").text
    assert '<form class="category__check"' not in body
    assert "Couldn&rsquo;t reach" not in body
    assert 'data-check=""' in body


def test_running_shows_the_status_url_and_the_no_js_form(payroll_trust) -> None:
    _connect("p01")
    state.set_check("p01", "meridian", state.Check(state="checking", token="t"))
    credential_id, token = _income(payroll_trust, n=1)
    _receive("p01", (credential_id, token))
    state.mark_seen("p01", [credential_id.removeprefix("urn:uuid:")])  # new_count 0, keeps the form
    body = client.get("/p/p01/credentials").text
    assert 'data-check="/p/p01/credentials/check"' in body
    form_start = body.index('class="category__check"')
    form_tag = body[form_start - 20 : form_start + 80]
    assert "hidden" not in form_tag
    assert 'action="/p/p01/credentials"' in form_tag


def test_error_shows_the_note_and_check_again(payroll_trust) -> None:
    _connect("p01")
    state.set_check(
        "p01", "meridian", state.Check(state="done", token="t", result="error", finished_at=clock.now())
    )
    _receive("p01", _income(payroll_trust, n=1))
    body = client.get("/p/p01/credentials").text
    assert "Couldn&rsquo;t reach Meridian Payroll to check for new credentials." in body
    assert ">Check again<" in body
    assert '<form class="category__check"' not in body


def test_lost_connection_keeps_the_cards_and_offers_finish_connecting(payroll_trust) -> None:
    _connect("p01")
    state.get_link("p01", "meridian").connected_at = None  # fetch() already cleared it
    state.get_link("p01", "meridian").connection_id = None
    _receive("p01", _income(payroll_trust, n=1))
    body = client.get("/p/p01/credentials").text
    assert "Pinecrest Home Care" in body  # the card is still shown
    assert "Connect to Meridian Payroll again to keep receiving your pay as credentials." in body
    assert '<a class="btn btn--secondary" href="/p/p01/connections">Finish connecting</a>' in body
    assert "<script" not in body  # not connected: no live check to run
