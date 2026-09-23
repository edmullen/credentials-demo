"""Grouping the Wallet's Activity log by day, newest first (docs/design.md §6)."""

from itertools import groupby

from app import state
from app.display import EASTERN, day_heading, time_of_day


def grouped_events(person_id: str) -> list[dict]:
    events = sorted(state.events_for(person_id), key=lambda e: e.at, reverse=True)
    groups = []
    for _, day_events in groupby(events, key=lambda e: e.at.astimezone(EASTERN).date()):
        day_events = list(day_events)
        groups.append({
            "heading": day_heading(day_events[0].at),
            "events": [
                {"time": time_of_day(e.at), "dot": e.dot, "message": e.message}
                for e in day_events
            ],
        })
    return groups
