import json

import pytest
from django.core.cache import cache
from django.test import Client

PASSWORD = "un mot de passe solide"


class Browser:
    """Navigateur de test : garde ses cookies et envoie le jeton CSRF comme l'application Vue."""

    def __init__(self) -> None:
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = ""
        self.refresh()

    def refresh(self) -> dict:
        data = self.client.get("/api/session").json()
        self.csrf = data["csrf"]
        return data

    def request(self, method: str, path: str, data: dict | None = None, *, csrf: bool = True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf} if csrf else {}
        response = getattr(self.client, method)(
            path, json.dumps(data or {}), content_type="application/json", **headers
        )
        body = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        if isinstance(body, dict) and "csrf" in body:
            self.csrf = body["csrf"]
        response.data = body
        return response

    def get(self, path: str):
        response = self.client.get(path)
        response.data = (
            response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        )
        return response

    def post(self, path: str, data: dict | None = None, **kwargs):
        return self.request("post", path, data, **kwargs)

    def delete(self, path: str):
        return self.request("delete", path)

    def register(self, pseudo: str = "alice", email: str | None = None, password: str = PASSWORD):
        return self.post(
            "/api/inscription", {"pseudo": pseudo, "email": email or f"{pseudo}@exemple.fr", "mot_de_passe": password}
        )


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def browser(db):
    return Browser()


@pytest.fixture
def make_browser(db):
    return Browser


@pytest.fixture
def two_players(db):
    """Alice crée une partie avec les blancs, Bruno la rejoint."""
    alice, bruno = Browser(), Browser()
    alice.register("alice")
    bruno.register("bruno")
    code = alice.post("/api/parties", {"couleur": "w"}).data["partie"]["code"]
    bruno.post(f"/api/parties/{code}/rejoindre")
    return alice, bruno, code
