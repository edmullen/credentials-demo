"""Wake the other two apps on startup.

Render's free tier spins services down when idle, so each app pings its peers' /health once
when it starts. Fire and forget: a peer being down must never stop this app starting.

TEMPORARY: the ping isn't waking sleeping peers on Render and the cause isn't known yet
(docs/design.md §12, item 10), so every attempt prints one line to stdout, which Render's Logs
tab captures. Remove the prints once the cause is found and fixed.
"""

import asyncio
import os

import httpx

PEER_ENV_VARS = ('PAYROLL_URL', 'BENEFITS_URL')
# A sleeping Render service can take up to a minute to answer, and hanging up sooner may abandon
# the wake-up. Safe to wait this long: the ping is a background task that never delays startup.
TIMEOUT_SECONDS = 65


async def _ping(origin: str) -> None:
    target = origin.rstrip("/") + "/health"
    print(f"[peer-wake] pinging {target}", flush=True)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(target)
        print(f"[peer-wake] {target} -> {response.status_code}", flush=True)
    except Exception as exc:
        print(f"[peer-wake] {target} failed: {exc!r}", flush=True)


def wake_peers() -> list[asyncio.Task]:
    """Start one background ping per configured peer, without waiting for any answer.

    A peer whose environment variable is unset is skipped, so locally and in CI nothing runs.
    """
    origins = [os.environ.get(name, "").strip() for name in PEER_ENV_VARS]
    configured = [o for o in origins if o]
    print(f"[peer-wake] {PEER_ENV_VARS} -> {configured or 'none configured'}", flush=True)
    return [asyncio.create_task(_ping(origin)) for origin in configured]
