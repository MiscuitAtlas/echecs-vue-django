"""Pages de l'application Vue et en-têtes de sécurité."""


def test_every_page_address_returns_the_vue_application(client, settings, tmp_path):
    (tmp_path / "index.html").write_text('<div id="app"></div>')
    settings.FRONTEND_DIST = tmp_path

    for path in ["/", "/parties", "/parties/K7Q2XA", "/compte"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b'<div id="app">' in b"".join(response.streaming_content)
        assert response["Cache-Control"] == "no-cache"


def test_security_headers(client):
    response = client.get("/api/session")

    policy = response["Content-Security-Policy"]
    assert "script-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response.cookies["csrftoken"]["httponly"]


def test_unknown_api_address_answers_in_json(client):
    response = client.get("/api/nexiste/pas")
    assert response.status_code == 404
    assert response.json() == {"erreur": "Adresse d'API inconnue."}
