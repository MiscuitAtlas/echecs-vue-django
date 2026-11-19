"""WebSocket d'une partie : chaque joueur reçoit les coups et les messages de l'autre."""

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator

from config.asgi import application

from .conftest import Browser

pytestmark = [pytest.mark.asyncio, pytest.mark.django_db(transaction=True)]


def connect(code: str, browser: Browser | None = None, origin: str = "http://localhost"):
    headers = [(b"origin", origin.encode())]
    if browser is not None:
        cookies = "; ".join(f"{name}={morsel.value}" for name, morsel in browser.client.cookies.items())
        headers.append((b"cookie", cookies.encode()))
    return WebsocketCommunicator(application, f"/ws/parties/{code}/", headers=headers)


@sync_to_async
def start_game():
    alice, bruno = Browser(), Browser()
    alice.register("alice")
    bruno.register("bruno")
    code = alice.post("/api/parties", {"couleur": "w"}).data["partie"]["code"]
    bruno.post(f"/api/parties/{code}/rejoindre")
    return alice, bruno, code


async def test_players_receive_moves_and_messages():
    alice, bruno, code = await start_game()
    socket = connect(code, bruno)
    connected, _ = await socket.connect()
    assert connected
    first = await socket.receive_json_from()
    assert (first["type"], first["partie"]["trait"], first["partie"]["ma_couleur"]) == ("partie", "w", "b")

    await sync_to_async(alice.post)(f"/api/parties/{code}/coups", {"coup": "e2e4", "demi_coup": 0})
    update = await socket.receive_json_from()
    assert update["partie"]["coups"] == [{"san": "e4", "uci": "e2e4"}]
    assert len(update["partie"]["coups_possibles"]) == 20  # vue personnelle de Bruno, qui a le trait

    await sync_to_async(alice.post)(f"/api/parties/{code}/messages", {"texte": "à toi"})
    message = await socket.receive_json_from()
    assert (message["type"], message["message"]["texte"]) == ("message", "à toi")
    await socket.disconnect()


async def test_only_the_two_players_can_listen():
    _, _, code = await start_game()
    outsider = await sync_to_async(Browser)()
    await sync_to_async(outsider.register)("chloe")

    for browser in (None, outsider):
        socket = connect(code, browser)
        await socket.connect()
        closed = await socket.receive_output()
        assert (closed["type"], closed["code"]) == ("websocket.close", 4403)


async def test_other_websites_cannot_open_the_connection():
    _, bruno, code = await start_game()
    socket = connect(code, bruno, origin="https://site-pirate.example")
    connected, _ = await socket.connect()
    assert not connected
