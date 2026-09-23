"""The compact page head and the step lines under it (docs/design.md §3)."""

import re

import pytest
from fastapi.testclient import TestClient

from app.connections import connections_title
from app.main import app

client = TestClient(app)


def _head(body: str) -> tuple[str | None, str]:
    """The page head's back-link text (or None) and its <h1> text."""
    head = re.search(r'<div class="pagehead">(.*?)</div>', body, re.S).group(1)
    back = re.search(r'<a class="back" href="[^"]+">([^<]+)</a>', head)
    name = re.search(r'<h1 class="pagehead__name">([^<]+)</h1>', head).group(1)
    return (back.group(1) if back else None), name


@pytest.mark.parametrize("path, back, name, step", [
    ("/p/p01/credentials", None, "Credentials", None),
    ("/p/p01/connections", None, "Connections", "You have 0 connections"),
    ("/p/p01/connections/employers", "Connections", "Find your employer", "Select your employer"),
    ("/p/p01/activity", None, "Activity", None),
    ("/p/p01/switch", None, "Demo control", "Switch person"),
])
def test_each_page_opens_with_its_page_head(path, back, name, step) -> None:
    body = client.get(path).text
    assert _head(body) == (back, name)
    assert f"<title>{name} — Wallet</title>" in body
    steps = re.findall(r'<p class="intro__title">([^<]+)</p>', body)
    assert steps == ([step] if step else [])
    assert 'class="intro__eyebrow">Wallet<' not in body


def test_the_credential_detail_page_keeps_the_name_as_its_step_line() -> None:
    href = re.search(r'href="(/p/p01/credentials/[^"]+)"', client.get("/p/p01/credentials").text).group(1)
    body = client.get(href).text
    assert _head(body) == ("All credentials", "Identity credential")
    assert '<p class="intro__title">Grace Okafor</p>' in body


def test_there_is_one_h1_per_page() -> None:
    for path in ("/p/p01/credentials", "/p/p01/connections", "/p/p01/connections/employers"):
        assert client.get(path).text.count("<h1") == 1


def test_a_separator_only_appears_with_a_back_link() -> None:
    assert "pagehead__sep" not in client.get("/p/p01/connections").text
    assert 'class="pagehead__sep" aria-hidden="true">|<' in client.get("/p/p01/connections/employers").text


def test_connections_asks_for_the_next_step_once_an_employer_is_added() -> None:
    client.post("/p/p01/connections/employers", data={"employer": "pinecrest"})
    body = client.get("/p/p01/connections").text
    assert '<p class="intro__title">Now connect your payroll</p>' in body


@pytest.mark.parametrize("panels, title", [
    ([], "You have 0 connections"),
    ([{"connected": True}], "You have 1 connection"),
    ([{"connected": True}, {"connected": True}], "You have 2 connections"),
    ([{"connected": False}], "Now connect your payroll"),
    ([{"connected": True}, {"connected": False}], "Now connect your payroll"),
])
def test_connections_title(panels, title) -> None:
    assert connections_title(panels) == title
