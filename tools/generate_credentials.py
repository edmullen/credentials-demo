# /// script
# requires-python = ">=3.12"
# dependencies = ["pyjwt[crypto]>=2.9", "cryptography<49"]
# ///
"""Generate the Wallet's data: keys, trust list, and signed identity credentials.

Run by hand from the repo root:

    uv run tools/generate_credentials.py

Reads   tools/sample_data/generated/{people,employers}.json, tools/sample_data/photos/pNN.jpg
Writes  keys/{nj,mi,ny,oh}-1.jwk.json    private keys, gitignored
        apps/wallet/app/data/{people,credentials,trust}.json
        apps/payroll/app/data/trust.json

A one-shot generator with committed output, as docs/decisions.md allows: nothing runs it at
build or deploy time. Keys are disposable (docs/credential-model.md §2): every run replaces
every key and every signature. Credential ids are name-based, so they survive a re-run and the
Wallet's detail-page URLs stay the same.

What it builds is docs/design.md §2–3: one ES256 key pair per state, one signed identity
credential for each person whose `identity` is not "none", and the two deliberately tampered
credentials the sample data asks for. Payroll's and Benefits' keys arrive in Loops 5 and 6;
issuers are data here, so adding them is an entry in ISSUERS, not new code.

`cryptography<49` is deliberate: 49 and later publish no wheel for Intel Macs, and building it
from source needs OpenSSL and pkg-config. The Wallet's pyproject carries the same cap.
"""

import base64
import hashlib
import json
import uuid
from datetime import date, timedelta
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PEOPLE = ROOT / "tools" / "sample_data" / "generated" / "people.json"
SAMPLE_EMPLOYERS = ROOT / "tools" / "sample_data" / "generated" / "employers.json"
PHOTOS = ROOT / "tools" / "sample_data" / "photos"
KEYS_DIR = ROOT / "keys"
WALLET_DATA = ROOT / "apps" / "wallet" / "app" / "data"
PAYROLL_DATA = ROOT / "apps" / "payroll" / "app" / "data"

# Same namespace the sample data uses for name-based ids (tools/generate_sample_data.py).
NAMESPACE = uuid.UUID("6f1c2a4e-2d7b-5c1e-9a3f-0b8d4e7c1a52")

# The four states, keyed by the address region of the people they issue to.
ISSUERS = {
    "NJ": {"id": "did:example:state-of-new-jersey", "name": "State of New Jersey", "kid": "nj-1"},
    "MI": {"id": "did:example:state-of-michigan", "name": "State of Michigan", "kid": "mi-1"},
    "NY": {"id": "did:example:state-of-new-york", "name": "State of New York", "kid": "ny-1"},
    "OH": {"id": "did:example:state-of-ohio", "name": "State of Ohio", "kid": "oh-1"},
}
TRUSTED_FOR = ["IdentityCredential"]

# credential-model §5: identity credentials issue in the first half of 2026 and last four
# years, so none expires mid-demo and no test depends on today's date.
ISSUE_WINDOW_START = date(2026, 1, 1)
ISSUE_WINDOW_DAYS = 181  # through 30 June
VALIDITY_YEARS = 4

# A 40x50 flat-grey JPEG. Carmen Diaz's credential is signed over this, then her real photo is
# swapped in, so the signature genuinely fails (docs/design.md §3). A constant, so no extra
# file joins tools/sample_data/photos/.
PLACEHOLDER_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABQODxIPDRQSEBIXFRQYHjIhHhwcHj0sLiQySUBMS0dARkVQWnNiUFVt"
    "VkVGZIhlbXd7gYKBTmCNl4x9lnN+gXz/2wBDARUXFx4aHjshITt8U0ZTfHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8"
    "fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHz/wAARCAAyACgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAA"
    "AAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAk"
    "M2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QA"
    "HwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdh"
    "cRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hp"
    "anN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk"
    "5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDdooopgFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQA"
    "UUUUAFFFFABRRRQB/9k="
)


def data_uri(jpeg_b64: str) -> str:
    return f"data:image/jpeg;base64,{jpeg_b64}"


def photo_uri(person: dict) -> str:
    return data_uri(base64.b64encode((PHOTOS / person["photo"]).read_bytes()).decode())


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---- Keys -------------------------------------------------------------------------------------


def make_keys() -> dict[str, dict]:
    """A fresh P-256 pair per state: {region: {"private": jwk, "public": jwk, "key": key}}."""
    keys = {}
    for region, issuer in ISSUERS.items():
        key = ec.generate_private_key(ec.SECP256R1())
        private = json.loads(ECAlgorithm.to_jwk(key))
        public = json.loads(ECAlgorithm.to_jwk(key.public_key()))
        for jwk in (private, public):
            jwk["kid"] = issuer["kid"]
        keys[region] = {"key": key, "private": private, "public": public}
    return keys


def write_keys(keys: dict[str, dict]) -> None:
    KEYS_DIR.mkdir(exist_ok=True)
    for region, pair in keys.items():
        path = KEYS_DIR / f"{ISSUERS[region]['kid']}.jwk.json"
        path.write_text(json.dumps(pair["private"], indent=2) + "\n")


def trust_list(keys: dict[str, dict]) -> dict:
    return {
        issuer["id"]: {
            "name": issuer["name"],
            "trustedFor": TRUSTED_FOR,
            "keys": [keys[region]["public"]],
        }
        for region, issuer in ISSUERS.items()
    }


# ---- Credentials ------------------------------------------------------------------------------


def credential_id(person: dict) -> str:
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, person['id'] + ':IdentityCredential')}"


def validity(person: dict) -> tuple[str, str]:
    """Spread deterministically over the issue window from the person id."""
    offset = int.from_bytes(hashlib.sha256(person["id"].encode()).digest()[:4]) % ISSUE_WINDOW_DAYS
    start = ISSUE_WINDOW_START + timedelta(days=offset)
    end = start.replace(year=start.year + VALIDITY_YEARS)
    return f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T00:00:00Z"


def postal_address(address: dict) -> dict:
    return {
        "type": "PostalAddress",
        "streetAddress": address["street"],
        "addressLocality": address["locality"],
        "county": address["county"],  # the one documented extension (credential-model §3)
        "addressRegion": address["region"],
        "postalCode": address["postal_code"],
    }


def identity_payload(person: dict, issuer: dict, image: str) -> dict:
    valid_from, valid_until = validity(person)
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "id": credential_id(person),
        "type": ["VerifiableCredential", "IdentityCredential"],
        "issuer": {"id": issuer["id"], "name": issuer["name"]},
        "validFrom": valid_from,
        "validUntil": valid_until,
        "credentialSubject": {
            "id": person["subjectId"],
            "givenName": person["givenName"],
            "familyName": person["familyName"],
            "birthDate": person["birthDate"],
            "image": image,
            "address": postal_address(person["address"]),
        },
    }


def sign(payload: dict, key, kid: str) -> str:
    # The payload *is* the credential: no `vc` wrapper, no iss/sub/exp (credential-model §3–4).
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "vc+jwt"})


def substitute_payload(token: str, change) -> str:
    """Tamper after signing: alter the payload, keep the original header and signature."""
    header, payload, signature = token.split(".")
    claims = json.loads(b64url_decode(payload))
    change(claims)
    encoded = json.dumps(claims, separators=(",", ":")).encode()
    return ".".join([header, b64url(encoded), signature])


def issue(person: dict, keys: dict[str, dict]) -> str:
    region = person["address"]["region"]
    issuer = ISSUERS[region]
    tamper = person.get("tamper")
    real_image = photo_uri(person)
    # A photo tamper is signed over the placeholder and given the real face afterwards.
    signed_image = data_uri(PLACEHOLDER_JPEG_B64) if tamper and tamper["kind"] == "photo" else real_image
    token = sign(identity_payload(person, issuer, signed_image), keys[region]["key"], issuer["kid"])
    if not tamper:
        return token
    if tamper["kind"] == "address":
        claimed = postal_address(tamper["claimed_address"])
        return substitute_payload(token, lambda c: c["credentialSubject"].update(address=claimed))
    if tamper["kind"] == "photo":
        return substitute_payload(token, lambda c: c["credentialSubject"].update(image=real_image))
    raise SystemExit(f"{person['id']}: unknown tamper kind {tamper['kind']!r}")


# ---- Output -----------------------------------------------------------------------------------


def wallet_person(person: dict, employer_names: dict[str, str]) -> dict:
    """Only what a screen shows. No identity status: the badge comes from verifying.

    `employerNames` is a demo aid for the person switcher, in job order (Loop 4a,
    docs/design.md §7). The Wallet's connect logic never reads it: whether someone works for an
    employer is Payroll's call.
    """
    return {
        "id": person["id"],
        "givenName": person["givenName"],
        "familyName": person["familyName"],
        "initials": person["givenName"][0] + person["familyName"][0],
        "locality": person["address"]["locality"],
        "region": person["address"]["region"],
        "employerNames": [employer_names[job["employerId"]] for job in person["jobs"]],
    }


def write_json(name: str, data, directory: Path = WALLET_DATA) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    people = sorted(json.loads(SAMPLE_PEOPLE.read_text()), key=lambda p: p["id"])
    employer_names = {e["id"]: e["name"] for e in json.loads(SAMPLE_EMPLOYERS.read_text())}
    keys = make_keys()

    holders = [p for p in people if p["identity"] != "none"]
    for person in holders:
        if person["address"]["region"] not in ISSUERS:
            raise SystemExit(f"{person['id']}: no issuer for {person['address']['region']}")
    credentials = {p["id"]: [issue(p, keys)] if p["identity"] != "none" else [] for p in people}

    write_keys(keys)
    write_json("people.json", [wallet_person(p, employer_names) for p in people])
    write_json("credentials.json", credentials)
    write_json("trust.json", trust_list(keys))
    # Payroll trusts the same four states, until it gets its own keys in Loop 5
    # (docs/design.md §7). Kept in step with the Wallet's, so a re-run can't leave one behind.
    write_json("trust.json", trust_list(keys), directory=PAYROLL_DATA)

    tampered = [p["id"] for p in holders if p.get("tamper")]
    print(f"Keys:        {len(keys)} written to keys/ (gitignored)")
    print(f"Credentials: {len(holders)} signed, {len(tampered)} tampered ({', '.join(tampered)})")
    print(f"People:      {len(people)}; {len(people) - len(holders)} hold nothing")


if __name__ == "__main__":
    main()
