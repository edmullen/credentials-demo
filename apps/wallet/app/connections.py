"""Wallet-side view and transition logic for Connections and Activity (docs/design.md §4, §6).

Activity entries are written here, at the transitions, never by a GET (docs/design.md §5).
"""

from app import clock, state
from app.credentials import find_credential
from app.display import join_and, when
from app.outcomes import CONNECTION_STATES, connection_sentences
from app.providers import all_providers, get_employer, provider_for_employer
from app.verify import Outcome

CHECK_STATUS_URL = "/p/{person_id}/credentials/check"


def employer_names(employer_ids: list[str]) -> list[str]:
    """Employer names for these ids, A-Z."""
    return sorted(get_employer(e)["name"] for e in employer_ids)


def connections_title(panels: list[dict]) -> str:
    """The Connections step title (docs/design.md §4): the next step, or the count so far."""
    if any(not panel["connected"] for panel in panels):
        return "Now connect your payroll"
    count = sum(1 for panel in panels if panel["connected"])
    return f"You have {count} connection{'' if count == 1 else 's'}"


def income_note(person_id: str) -> dict:
    """Which Income note the credentials page shows (docs/design.md §6): "start" with no link,
    "chosen" with an employer added but not connected (including after a failed attempt), or
    "connected". "chosen" names the most recently added employer."""
    for provider_id, provider in all_providers().items():
        if provider["kind"] != "payroll":
            continue
        link = state.get_link(person_id, provider_id)
        if link is None:
            continue
        if link.connected_at is not None:
            return {"state": "connected", "provider": provider["name"]}
        return {
            "state": "chosen",
            "provider": provider["name"],
            "employer": get_employer(link.employers[-1])["name"],
        }
    return {"state": "start"}


def income_check_view(person_id: str) -> dict | None:
    """What the Credentials page's Income section shows below the cards, and the heading's
    `data-check` (docs/design.md §9, §10). None when the person has never linked a provider.

    While connected: {"connected": True, "running": ..., "error": ..., "status_url": ...} — the
    §9 table's four rows collapse to two booleans, since "finished with unseen cards" and
    "finished none" both mean "not running, not the error state".

    After a lost connection (§13 item 4): {"connected": False, "provider_name": ...} — the
    person still holds their income cards, but needs to reconnect.
    """
    for provider_id, provider in all_providers().items():
        if provider["kind"] != "payroll":
            continue
        link = state.get_link(person_id, provider_id)
        if link is None:
            continue
        if link.connected_at is None:
            return {"connected": False, "provider_name": provider["name"]}
        check = state.get_check(person_id, provider_id)
        running = check is not None and check.state == "checking"
        error = check is not None and check.state == "done" and check.result == "error"
        return {
            "connected": True,
            "running": running,
            "error": error,
            "provider_name": provider["name"],
            "status_url": CHECK_STATUS_URL.format(person_id=person_id) if running else "",
        }
    return None


def _service_band(person_id: str, provider_name: str, link: state.Link) -> dict:
    """A service's connected band names how many benefit credentials it sent instead of
    Payroll's per-employer sentence, and leaves that line out at zero (docs/design.md §10.9)."""
    from app.credentials import credentials_for  # local import: avoids a cycle at module load

    s = CONNECTION_STATES["connected"]
    held = sum(1 for c in credentials_for(person_id) if c.category == "Benefits")
    sentences = [f"Connected since {when(link.connected_at)}."]
    if held:
        sentences.append(f"{provider_name} sent you {held} benefit credential{'' if held == 1 else 's'}.")
    return {
        "variant": s.variant, "glyph": s.glyph, "label": s.label,
        "sentences": sentences, "credential_link": None, "arrived": None,
    }


def band_for(person_id: str, provider_name: str, link: state.Link, kind: str = "payroll") -> dict | None:
    """The provider panel's status band, or None when there's nothing to say yet."""
    if link.connected_at:
        if kind == "service":
            return _service_band(person_id, provider_name, link)
        s = CONNECTION_STATES["connected"]
        sentences = connection_sentences("connected", provider_name, when(link.connected_at))
        arrived = link.arrived
        link.arrived = None  # the line shows once; this GET is what "once" means (§9)
        return {
            "variant": s.variant, "glyph": s.glyph, "label": s.label,
            "sentences": sentences, "credential_link": None, "arrived": arrived,
        }
    if link.outcome:
        s = CONNECTION_STATES[link.outcome]
        sentences = connection_sentences(link.outcome, provider_name)
        credential_link = None
        if link.outcome == "credential_invalid" and link.shared_credential_id:
            cred = find_credential(person_id, link.shared_credential_id)
            if cred is not None and cred.outcome is Outcome.TAMPERED:
                credential_link = f"/p/{person_id}/credentials/{link.shared_credential_id}"
        return {
            "variant": s.variant, "glyph": s.glyph, "label": s.label,
            "sentences": sentences, "credential_link": credential_link,
        }
    return None


def provider_panels(person_id: str) -> list[dict]:
    """One panel per provider the person has a link to, services above payroll providers —
    "newest first" in the only order this loop's demo produces (docs/design.md §10.9)."""
    panels = []
    for provider_id, provider in all_providers().items():
        link = state.get_link(person_id, provider_id)
        if link is None:
            continue
        panels.append({
            "provider_id": provider_id,
            "name": provider["name"],
            "kind": provider["kind"],
            "employers": employer_names(link.employers),
            "connected": link.connected_at is not None,
            "band": band_for(person_id, provider["name"], link, provider["kind"]),
        })
    panels.sort(key=lambda p: p["kind"] != "service")
    return panels


def add_employer(person_id: str, employer_id: str) -> dict | None:
    """Adds the employer under its provider and logs it, unless it's already there.

    Returns the employer, or None if `employer_id` isn't a real employer.
    """
    employer = get_employer(employer_id)
    provider_id = provider_for_employer(employer_id)
    if employer is None or provider_id is None:
        return None
    provider = all_providers()[provider_id]
    existing = state.get_link(person_id, provider_id)
    already_added = existing is not None and employer_id in existing.employers
    state.add_employer(person_id, provider_id, employer_id)
    if not already_added:
        state.log(
            person_id, "neutral",
            f"{employer['name']} added, paid through {provider['name']}",
            clock.now(),
        )
    return employer


def remove_link(person_id: str, provider_id: str) -> dict | None:
    """Removes the link and logs Remove or Disconnect, whichever it was.

    Returns the removed link, or None if there wasn't one. Makes no call to Payroll.
    """
    provider = all_providers().get(provider_id)
    if provider is None:
        return None
    link = state.remove_link(person_id, provider_id)
    if link is None:
        return None
    if provider["kind"] == "service":
        # A service has no employers, so Payroll's "…removed, with {employers}" doesn't apply
        # (docs/design.md §10.9); Remove always reads this way, connected or not.
        message = f"{provider['name']} removed"
    elif link.connected_at is not None:
        message = f"Disconnected from {provider['name']}"
    else:
        message = f"{provider['name']} removed, with {join_and(employer_names(link.employers))}"
    state.log(person_id, "neutral", message, clock.now())
    return link
