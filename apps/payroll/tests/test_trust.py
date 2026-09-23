import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "app" / "data"


def test_trust_list_has_four_states_trusted_for_identity_only() -> None:
    trust = json.loads((DATA_DIR / "trust.json").read_text())
    assert len(trust) == 4
    for issuer in trust.values():
        assert issuer["trustedFor"] == ["IdentityCredential"]
        assert len(issuer["keys"]) == 1
        assert issuer["keys"][0]["kty"] == "EC"
        assert issuer["keys"][0]["crv"] == "P-256"


def test_trust_list_is_byte_identical_to_the_wallets() -> None:
    wallet_trust = Path(__file__).parent.parent.parent / "wallet" / "app" / "data" / "trust.json"
    assert (DATA_DIR / "trust.json").read_bytes() == wallet_trust.read_bytes()
