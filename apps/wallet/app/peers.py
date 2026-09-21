"""Wake the other two apps on startup.

Render's free tier spins services down when idle, so each app pings its peers' /health once
when it starts. Fire and forget: a peer being down must never stop this app starting.
"""

import asyncio
import os

import httpx

PEER_ENV_VARS = ('PAYROLL_URL', 'BENEFITS_URL')
# A sleeping Render service can take up to a minute to answer, and hanging up sooner may abandon
# the wake-up. Safe to wait this long: the ping is a background task that never delays startup.
TIMEOUT_SECONDS = 65


async def _ping(origin: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            await client.get(origin.rstrip("/") + "/health")
    except Exception:
        pass


def wake_peers() -> list[asyncio.Task]:
    """Start one background ping per configured peer, without waiting for any answer.

    A peer whose environment variable is unset is skipped, so locally and in CI nothing runs.
    """
    origins = [os.environ.get(name, "").strip() for name in PEER_ENV_VARS]
    return [asyncio.create_task(_ping(origin)) for origin in origins if origin]
