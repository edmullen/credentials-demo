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


def test_trust_list_matches_the_wallets_four_states() -> None:
    # Payroll's own trust.json never gained Payroll's or Benefit Agency's entry (it doesn't
    # verify its own credentials, and it never sees a BenefitCredential, docs/design.md §3), so
    # it's the Wallet's minus those two entries.
    wallet_trust = json.loads(
        (Path(__file__).parent.parent.parent / "wallet" / "app" / "data" / "trust.json").read_text()
    )
    payroll_trust = json.loads((DATA_DIR / "trust.json").read_text())
    del wallet_trust["https://cred-demo-payroll.onrender.com"]
    del wallet_trust["https://cred-demo-benefits.onrender.com"]
    assert payroll_trust == wallet_trust
