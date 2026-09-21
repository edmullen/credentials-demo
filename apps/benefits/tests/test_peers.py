import asyncio

import httpx

from app import peers


def _run(coro):
    return asyncio.run(coro)


def test_unset_urls_start_no_pings(monkeypatch) -> None:
    for name in peers.PEER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(peers, "_ping", lambda origin: (_ for _ in ()).throw(AssertionError(origin)))

    async def go():
        return peers.wake_peers()

    assert _run(go()) == []


def test_each_configured_peer_gets_one_ping(monkeypatch) -> None:
    seen: list[str] = []

    async def fake_ping(origin: str) -> None:
        seen.append(origin)

    for name in peers.PEER_ENV_VARS:
        monkeypatch.setenv(name, f"https://{name.lower()}.example")
    monkeypatch.setattr(peers, "_ping", fake_ping)

    async def go():
        await asyncio.gather(*peers.wake_peers())

    _run(go())
    assert sorted(seen) == sorted(f"https://{name.lower()}.example" for name in peers.PEER_ENV_VARS)


def test_ping_requests_health_on_the_peer(monkeypatch) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(peers.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw))
    _run(peers._ping("https://peer.example/"))
    assert requested == ["https://peer.example/health"]


def test_ping_swallows_a_peer_that_is_down(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(peers.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw))
    _run(peers._ping("https://peer.example"))  # must not raise
