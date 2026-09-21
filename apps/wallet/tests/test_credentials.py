import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import credentials
from app.credentials import credentials_for
from app.main import app
from app.people import DATA_DIR

client = TestClient(app)
TAMPERED = {"p22": "State of New York", "p23": "State of New Jersey"}


def _detail_url(person_id: str) -> str:
    (view,) = credentials_for(person_id)
    return f"/p/{person_id}/credentials/{view.id}"


def test_p08_home_shows_a_verified_credential() -> None:
    body = client.get("/p/p08/credentials").text
    assert "State of New Jersey" in body
    assert "Nadia Haddad" in body and "145 Main Street" in body and "Paterson, NJ 07501" in body
    assert 'class="badge badge--verified"' in body and ">Verified<" in body
    assert re.search(r"Valid until \d{1,2} \w{3} 2030", body)
    assert "Income" in body and "None yet" in body


def test_credential_ids_are_uuid5_and_stable_in_committed_data() -> None:
    (view,) = credentials_for("p08")
    assert view.id == "8dd4fca0-7481-5188-b2e0-db3ea274b4e5"


def test_photo_is_rendered_from_the_credentials_own_image_claim() -> None:
    (view,) = credentials_for("p08")
    image = view.subject["image"]
    assert image.startswith("data:image/jpeg;base64,")
    body = client.get("/p/p08/credentials").text
    assert f'src="{image}"' in body
    assert 'alt="Nadia Haddad"' in body


def test_the_wallet_serves_no_photo_files() -> None:
    static = Path(__file__).parent.parent / "app" / "static"
    assert not [p for p in static.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]


def test_p08_detail_shows_status_message_claims_and_disclosure() -> None:
    body = client.get(_detail_url("p08")).text
    assert "Nothing in this credential has changed since the State of New Jersey issued it." in body
    assert "2 September 1991" in body and "New Jersey" in body and "Passaic" in body
    assert re.search(r"Valid from \d{1,2} \w+ 2026", body) and re.search(r"Valid until \d{1,2} \w+ 2030", body)
    assert "did:example:state-of-new-jersey" in body and "VerifiableCredential, IdentityCredential" in body
    assert "shown as it was received" not in body


@pytest.mark.parametrize("person_id", sorted(TAMPERED))
def test_tampered_home_and_detail_show_tampered(person_id: str) -> None:
    home = client.get(f"/p/{person_id}/credentials").text
    assert 'class="badge badge--error"' in home and ">Tampered<" in home
    detail = client.get(_detail_url(person_id)).text
    issuer = TAMPERED[person_id]
    assert f"was changed after the {issuer} issued it" in detail
    assert "shown as it was received" in detail
    assert "published key <code>" in detail and f"the {issuer}" in detail
    assert "Verified" not in detail


def test_victor_moreno_shows_an_nj_address_on_a_new_york_credential() -> None:
    body = client.get(_detail_url("p22")).text
    assert "State of New York" in body
    assert "310 Elmora Avenue" in body and "Elizabeth" in body and "Union" in body
    assert "480 Richmond Avenue" not in body


def test_carmen_diaz_shows_her_own_face_not_the_placeholder_that_was_signed() -> None:
    (view,) = credentials_for("p23")
    body = client.get(_detail_url("p23")).text
    assert f'src="{view.subject["image"]}"' in body
    # The signed image was a tiny placeholder (under 1 KB); the displayed one is a real portrait.
    assert len(view.subject["image"]) > 10_000


@pytest.mark.parametrize("person_id", ["p24", "p25"])
def test_people_with_no_credential_get_the_empty_state(person_id: str) -> None:
    body = client.get(f"/p/{person_id}/credentials").text
    assert 'class="empty"' in body
    assert '<button class="btn" type="button" disabled>Add Identity</button>' in body
    assert 'class="cred"' not in body


def test_a_credential_id_that_is_not_the_persons_is_404() -> None:
    (theirs,) = credentials_for("p01")
    assert client.get(f"/p/p08/credentials/{theirs.id}").status_code == 404
    assert client.get("/p/p08/credentials/not-a-credential").status_code == 404
    assert client.get(f"/p/p24/credentials/{theirs.id}").status_code == 404


def test_the_detail_link_on_the_home_page_resolves() -> None:
    body = client.get("/p/p08/credentials").text
    href = re.search(r'class="cred" href="([^"]+)"', body).group(1)
    assert client.get(href).status_code == 200


def test_switcher_badges_come_from_verification() -> None:
    body = client.get("/p/p08/switch").text
    labels = re.findall(r'<span class="badge badge--(\w+)"><span class="badge__icon"[^>]*>[^<]*</span>([^<]+)</span>', body)
    assert len(labels) == 25
    counts = {label: sum(1 for _, l in labels if l == label) for _, label in labels}
    assert counts == {"Verified": 21, "Tampered": 2, "No credential": 2}
    assert ("neutral", "No credential") in labels and ("error", "Tampered") in labels


def test_editing_a_committed_credential_by_hand_flips_it_to_tampered(monkeypatch) -> None:
    stored = json.loads((DATA_DIR / "credentials.json").read_text())
    trust = json.loads((DATA_DIR / "trust.json").read_text())
    header, payload, signature = stored["p08"][0].split(".")
    # Change the payload's street by hand, as someone editing the file would.
    import base64

    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["credentialSubject"]["address"]["streetAddress"] = "1 Forged Road"
    edited = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).rstrip(b"=").decode()
    stored["p08"][0] = ".".join([header, edited, signature])
    monkeypatch.setattr(credentials, "_committed", lambda: (stored, trust))

    home = client.get("/p/p08/credentials").text
    assert ">Tampered<" in home and "1 Forged Road" in home and ">Verified<" not in home


def test_no_private_key_material_in_the_wallets_data() -> None:
    for path in DATA_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        assert '"d":' not in json.dumps(data), path.name


def test_no_data_file_or_code_path_uses_a_tampered_flag() -> None:
    for name in ("people.json", "credentials.json", "trust.json"):
        text = (DATA_DIR / name).read_text().lower()
        assert '"tampered"' not in text and '"identity"' not in text
    for source in (Path(__file__).parent.parent / "app").glob("*.py"):
        code = source.read_text()
        assert '["tampered"]' not in code and 'get("tampered")' not in code, source.name
