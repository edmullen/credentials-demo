"""Wallet-side view and transition logic for Connections and Activity (docs/design.md §4, §6).

Activity entries are written here, at the transitions, never by a GET (docs/design.md §5).
"""

from app import clock, state
from app.credentials import find_credential
from app.display import join_and, when
from app.outcomes import CONNECTION_STATES, connection_sentences
from app.providers import all_providers, get_employer, provider_for_employer
from app.verify import Outcome


def employer_names(employer_ids: list[str]) -> list[str]:
    """Employer names for these ids, A-Z."""
    return sorted(get_employer(e)["name"] for e in employer_ids)


def band_for(person_id: str, provider_name: str, link: state.Link) -> dict | None:
    """The provider panel's status band, or None when there's nothing to say yet."""
    if link.connected_at:
        s = CONNECTION_STATES["connected"]
        sentences = connection_sentences("connected", provider_name, when(link.connected_at))
        return {
            "variant": s.variant, "glyph": s.glyph, "label": s.label,
            "sentences": sentences, "credential_link": None,
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
    """One panel per provider the person has a link to (only ever Meridian this loop)."""
    panels = []
    for provider_id, provider in all_providers().items():
        link = state.get_link(person_id, provider_id)
        if link is None:
            continue
        panels.append({
            "provider_id": provider_id,
            "name": provider["name"],
            "employers": employer_names(link.employers),
            "connected": link.connected_at is not None,
            "band": band_for(person_id, provider["name"], link),
        })
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
    if link.connected_at is not None:
        message = f"Disconnected from {provider['name']}"
    else:
        message = f"{provider['name']} removed, with {join_and(employer_names(link.employers))}"
    state.log(person_id, "neutral", message, clock.now())
    return link
