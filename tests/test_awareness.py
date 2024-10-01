import json

import pytest

from pycrdt_websocket.awareness import DEFAULT_USER, Awareness

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_default_user(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)

    assert awareness.user == DEFAULT_USER


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_set_user(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)
    user = {"username": "test_username", "name": "test_name"}
    awareness.user = user
    assert awareness.user == user


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_get_local_state(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)

    assert awareness.get_local_state() == {"user": DEFAULT_USER}


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_set_local_state_field(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)

    await awareness.set_local_state_field("new_field", "new_value")
    assert awareness.get_local_state() == {"user": DEFAULT_USER, "new_field": "new_value"}


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_get_changes(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)

    new_user = {
        "user": {
            "username": "2460ab00fd28415b87e49ec5aa2d482d",
            "name": "Anonymous Ersa",
            "display_name": "Anonymous Ersa",
            "initials": "AE",
            "avatar_url": None,
            "color": "var(--jp-collaborator-color7)",
        }
    }
    new_user_bytes = json.dumps(new_user, separators=(",", ":")).encode("utf-8")
    new_user_message = b"\xc3\x01\x01\xfa\xa1\x8f\x97\x03\x03\xba\x01" + new_user_bytes
    changes = awareness.get_changes(new_user_message)
    assert changes == {
        "added": [853790970],
        "updated": [],
        "filtered_updated": [],
        "removed": [],
        "states": [new_user],
    }
    assert awareness.states == {awareness.client_id: {"user": DEFAULT_USER}, 853790970: new_user}


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_observes(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider
    awareness = Awareness(ydoc)

    called = {}

    def callback(value):
        called.update(value)

    awareness.observe(callback)

    new_user = {
        "user": {
            "username": "2460ab00fd28415b87e49ec5aa2d482d",
            "name": "Anonymous Ersa",
            "display_name": "Anonymous Ersa",
            "initials": "AE",
            "avatar_url": None,
            "color": "var(--jp-collaborator-color7)",
        }
    }
    new_user_bytes = json.dumps(new_user, separators=(",", ":")).encode("utf-8")
    new_user_message = b"\xc3\x01\x01\xfa\xa1\x8f\x97\x03\x03\xba\x01" + new_user_bytes
    changes = awareness.get_changes(new_user_message)

    assert called == changes


@pytest.mark.parametrize("websocket_provider_connect", ["fake_websocket"], indirect=True)
async def test_awareness_on_change(yws_provider, websocket_provider_connect):
    ydoc, _ = yws_provider

    changes = []

    async def callback(value):
        changes.append(value)

    awareness = Awareness(ydoc, on_change=callback)

    await awareness.set_local_state_field("new_field", "new_value")

    assert len(changes) == 1

    assert type(changes[0]) is bytes
