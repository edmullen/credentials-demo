import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "app" / "data"


def test_trust_list_has_four_states_and_payroll() -> None:
    trust = json.loads((DATA_DIR / "trust.json").read_text())
    assert len(trust) == 5
    payroll = trust["https://cred-demo-payroll.onrender.com"]
    assert payroll["trustedFor"] == ["PaystubCredential"]
    for issuer_id, issuer in trust.items():
        if issuer_id == "https://cred-demo-payroll.onrender.com":
            continue
        assert issuer["trustedFor"] == ["IdentityCredential"]
    for issuer in trust.values():
        assert len(issuer["keys"]) == 1
        assert issuer["keys"][0]["kty"] == "EC"
        assert issuer["keys"][0]["crv"] == "P-256"
        assert "d" not in issuer["keys"][0]


def test_trust_list_matches_the_wallets_four_states_and_payroll() -> None:
    # Benefits verifies everything a presentation carries: identity credentials from the four
    # states, and paystubs from Payroll — but it never sees a BenefitCredential, since it's the
    # one issuing them (docs/design.md §3, §6).
    wallet_trust = json.loads(
        (Path(__file__).parent.parent.parent / "wallet" / "app" / "data" / "trust.json").read_text()
    )
    benefits_trust = json.loads((DATA_DIR / "trust.json").read_text())
    del wallet_trust["https://cred-demo-benefits.onrender.com"]
    assert benefits_trust == wallet_trust
