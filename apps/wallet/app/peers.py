"""Wake the other two apps on startup.

Render's free tier spins services down when idle, so each app pings its peers' /health once
when it starts. Fire and forget: a peer being down must never stop this app starting.

Confirmed on 2026-09-22 (docs/design.md §12, item 10): a sleeping Render service can reject a
wake-up outright with 429 ("hibernate-rate-limited") instead of queuing it and answering slowly.
Render's own docs and community reports describe this as expected free-tier behavior — the
caller is expected to retry, not treat it as a failure. _ping does that below.

TEMPORARY: every attempt still prints one line to stdout, which Render's Logs tab captures, to
confirm on the next cold-start test that retrying gets both peers past the 429. Remove the
prints once that's confirmed over a few tests.
"""

import asyncio
import os

import httpx

PEER_ENV_VARS = ("PAYROLL_URL", "BENEFITS_URL")
# A sleeping Render service can take up to a minute to answer once it actually starts responding.
# Safe to wait this long: the ping is a background task that never delays startup.
TIMEOUT_SECONDS = 65
# How long to keep retrying a 429 before giving up, and the pause between attempts. Community
# reports of this error put a successful wake anywhere from ~20s to several minutes out.
MAX_WAIT_SECONDS = 120
RETRY_INTERVAL_SECONDS = 5


async def _ping(origin: str) -> None:
    target = origin.rstrip("/") + "/health"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + MAX_WAIT_SECONDS
    attempt = 0
    while True:
        attempt += 1
        print(f"[peer-wake] pinging {target} (attempt {attempt})", flush=True)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(target)
        except Exception as exc:
            print(f"[peer-wake] {target} failed: {exc!r}", flush=True)
            return
        if response.status_code != 429 or loop.time() >= deadline:
            print(f"[peer-wake] {target} -> {response.status_code}", flush=True)
            return
        routing = response.headers.get("x-render-routing", "no x-render-routing header")
        print(
            f"[peer-wake] {target} -> 429 ({routing}), retrying in {RETRY_INTERVAL_SECONDS}s",
            flush=True,
        )
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)


def wake_peers() -> list[asyncio.Task]:
    """Start one background ping per configured peer, without waiting for any answer.

    A peer whose environment variable is unset is skipped, so locally and in CI nothing runs.
    """
    origins = [os.environ.get(name, "").strip() for name in PEER_ENV_VARS]
    configured = [o for o in origins if o]
    print(f"[peer-wake] {PEER_ENV_VARS} -> {configured or 'none configured'}", flush=True)
    return [asyncio.create_task(_ping(origin)) for origin in configured]
