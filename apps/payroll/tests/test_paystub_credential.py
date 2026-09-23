"""The paystub page's credential panel (docs/design.md §6, §14 item 8)."""

import jwt as pyjwt
from fastapi.testclient import TestClient

from app import clock, connections
from app.issuance import credential_id
from app.main import app
from app.paystubs import find_paystub

client = TestClient(app)

P01_16_30 = "b53638d6-8ff1-51a6-9e33-a6df833c8cba"  # Grace Okafor, Pinecrest


def test_panel_shows_alongside_the_paystub_when_not_connected() -> None:
    response = client.get(f"/p/p01/paystubs/{P01_16_30}")
    assert response.status_code == 200
    body = response.text
    assert '<h2 class="record__title" id="rec-paystub">Paystub</h2>' in body
    assert '<h2 class="record__title" id="rec-cred">Credential for this paystub</h2>' in body
    assert "sent to your wallet" not in body


def test_panel_shows_the_same_when_connected() -> None:
    connections.connect("p01", "Meridian Payroll", clock.now())
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    assert '<h2 class="record__title" id="rec-cred">Credential for this paystub</h2>' in body
    assert "sent to your wallet" not in body  # no delivery status, connected or not (intent)


def test_panel_shows_the_credential_id_and_claim_keys() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    stub = find_paystub("p01", P01_16_30)
    expected_id = credential_id(stub)
    assert body.count(expected_id) == 2  # the id band and the disclosure
    assert 'class="claim__key">payPeriodStart, payPeriodEnd<' in body
    assert 'class="claim__key">payDate<' in body
    assert 'class="claim__key">payFrequency<' in body
    assert 'class="claim__key">grossPay<' in body
    assert 'class="claim__key">netPay<' in body


def test_panel_values_match_the_paystubs() -> None:
    response = client.get(f"/p/p01/paystubs/{P01_16_30}")
    body = response.text
    assert body.count("Pinecrest Home Care") == 3  # <title>, paystub side, credential side
    assert body.count("$1,100.00") == 3  # earnings row, paystub's gross footer, credential's
    assert body.count("$955.87") == 2  # net, on both panels
    assert body.count("Semimonthly") == 2


def test_disclosure_holds_the_signed_jwt_and_no_employee_name() -> None:
    body = client.get(f"/p/p01/paystubs/{P01_16_30}").text
    assert "View signed credential" in body
    assert "cred-panel__omits" in body or "aren&rsquo;t in the credential" in body
    assert "Grace Okafor" not in body.split('id="rec-cred"')[1]  # not in the credential record
    stub = find_paystub("p01", P01_16_30)
    token_start = body.index('class="jwt">') + len('class="jwt">')
    token = body[token_start:body.index("<", token_start)]
    claims = pyjwt.decode(token, options={"verify_signature": False})
    assert claims["id"] == credential_id(stub)
    assert claims["credentialSubject"]["employer"]["name"] == "Pinecrest Home Care"
    assert "givenName" not in claims["credentialSubject"]
