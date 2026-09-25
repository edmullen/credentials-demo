"""The Wallet's outbound calls to a payroll provider (docs/design.md §3, §5).

One attempt, a 60-second timeout, no automatic retry — Loop 3's retry-on-429 never once
worked (design/loop-3/design.md §7), so there's nothing to gain from building another. The
Wallet identifies itself honestly, never disguised as a browser.
"""

import asyncio
from collections.abc import Coroutine
from urllib.parse import urljoin, urlsplit

import httpx

USER_AGENT = "cred-demo-wallet"
TIMEOUT = 60.0


def spawn(coro: Coroutine) -> asyncio.Task:
    """Runs `coro` as a detached task, outside the request that started it (docs/design.md §5).

    A seam: tests replace this with a collector, so they decide when a background call runs
    instead of depending on real timing.
    """
    return asyncio.create_task(coro)


def _same_origin(a: str, b: str) -> bool:
    ua, ub = urlsplit(a), urlsplit(b)
    return (ua.scheme, ua.netloc) == (ub.scheme, ub.netloc)


def resolve(provider_url: str, response_uri: str) -> str | None:
    """`response_uri` resolved against `provider_url`, or None if that lands off-origin.

    A path resolves onto the provider's own origin, as intended (docs/design.md §3). An
    absolute URI naming a different origin — malformed or malicious — resolves to itself,
    which then fails the origin check instead of silently being trusted.
    """
    resolved = urljoin(provider_url, response_uri)
    return resolved if _same_origin(provider_url, resolved) else None


async def get_json(url: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        return await client.get(url)


async def post_json(url: str, payload: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        return await client.post(url, json=payload)
