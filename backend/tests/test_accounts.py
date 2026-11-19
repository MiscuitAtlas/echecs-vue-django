"""Comptes : inscription, connexion, invités, mot de passe, suppression."""

from datetime import timedelta

from django.utils import timezone

from accounts.models import User

from .conftest import PASSWORD


def test_every_change_requires_the_csrf_token(browser):
    response = browser.post("/api/inscription", {"pseudo": "alice"}, csrf=False)

    assert response.status_code == 403
    assert "Session expirée" in response.data["erreur"]
    assert not User.objects.exists()


def test_registration_validates_each_field(browser):
    browser.register("alice")
    other = type(browser)()

    response = other.post("/api/inscription", {"pseudo": "ALICE", "email": "pas-un-email", "mot_de_passe": "1234"})

    assert response.status_code == 422
    assert set(response.data["champs"]) == {"pseudo", "email", "mot_de_passe"}
    assert "déjà pris" in response.data["champs"]["pseudo"]
    assert "trop court" in response.data["champs"]["mot_de_passe"]
    reserved = other.register("Invité-42")
    assert "réservé" in reserved.data["champs"]["pseudo"]


def test_registration_logs_in_and_hashes_the_password(browser):
    response = browser.register("alice", "Alice@Exemple.fr")

    assert response.status_code == 201
    assert response.data["utilisateur"]["pseudo"] == "alice"
    user = User.objects.get()
    assert user.email == "alice@exemple.fr"
    assert user.password.startswith("pbkdf2_sha256$")
    assert browser.refresh()["utilisateur"]["pseudo"] == "alice"


def test_login_gives_the_same_answer_for_unknown_email_and_wrong_password(browser, make_browser):
    browser.register("alice")
    visitor = make_browser()

    wrong = visitor.post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": "pas le bon"})
    unknown = visitor.post("/api/connexion", {"email": "personne@exemple.fr", "mot_de_passe": "pas le bon"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.data == unknown.data == {"erreur": "Email ou mot de passe incorrect."}
    ok = visitor.post("/api/connexion", {"email": " ALICE@exemple.fr ", "mot_de_passe": PASSWORD})
    assert ok.status_code == 200
    assert ok.data["utilisateur"]["pseudo"] == "alice"


def test_too_many_failures_lock_the_account_for_a_while(browser, make_browser):
    browser.register("alice")
    attacker = make_browser()
    for attempt in range(5):
        attacker.post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": f"essai {attempt}"})

    response = attacker.post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": PASSWORD})

    assert response.status_code == 429
    assert attacker.refresh()["utilisateur"] is None


def test_login_renews_the_session_and_the_csrf_token(browser, make_browser):
    browser.register("alice")
    visitor = make_browser()
    session_before = visitor.client.cookies.get("sessionid")
    csrf_before = visitor.csrf

    visitor.post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": PASSWORD})

    assert visitor.csrf != csrf_before
    assert visitor.client.cookies["sessionid"].value != getattr(session_before, "value", None)


def test_guest_account_then_registration_keeps_the_games(browser, make_browser):
    guest = browser.post("/api/invite")
    assert guest.status_code == 201
    assert guest.data["utilisateur"]["invite"] is True
    assert guest.data["utilisateur"]["pseudo"].startswith("Invité-")
    code = browser.post("/api/parties", {"couleur": "w"}).data["partie"]["code"]

    response = browser.register("camille")

    assert response.status_code == 201
    assert response.data["utilisateur"] == {
        "id": guest.data["utilisateur"]["id"],
        "pseudo": "camille",
        "email": "camille@exemple.fr",
        "invite": False,
    }
    assert browser.get("/api/parties").data["en_attente"][0]["code"] == code


def test_a_guest_account_disappears_at_logout(browser):
    browser.post("/api/invite")

    browser.post("/api/deconnexion")

    assert not User.objects.exists()


def test_old_guest_accounts_are_purged(browser, make_browser):
    browser.post("/api/invite")
    User.objects.update(date_joined=timezone.now() - timedelta(days=3), last_login=timezone.now() - timedelta(days=3))

    make_browser().post("/api/invite")

    assert User.objects.count() == 1


def test_changing_the_password_requires_the_current_one(browser, make_browser):
    browser.register("alice")

    refused = browser.post("/api/compte/mot-de-passe", {"actuel": "pas le bon", "nouveau": "nouveau mot de passe"})
    weak = browser.post("/api/compte/mot-de-passe", {"actuel": PASSWORD, "nouveau": "123"})
    ok = browser.post("/api/compte/mot-de-passe", {"actuel": PASSWORD, "nouveau": "nouveau mot de passe"})

    assert (refused.status_code, weak.status_code, ok.status_code) == (422, 422, 200)
    assert browser.refresh()["utilisateur"]["pseudo"] == "alice"
    login = make_browser().post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": "nouveau mot de passe"})
    assert login.status_code == 200


def test_changing_the_password_closes_the_other_sessions(browser, make_browser):
    browser.register("alice")
    phone = make_browser()
    phone.post("/api/connexion", {"email": "alice@exemple.fr", "mot_de_passe": PASSWORD})

    browser.post("/api/compte/mot-de-passe", {"actuel": PASSWORD, "nouveau": "nouveau mot de passe"})

    assert phone.refresh()["utilisateur"] is None


def test_account_deletion_requires_the_password_and_forfeits_ongoing_games(two_players):
    alice, bruno, code = two_players

    assert alice.post("/api/compte/suppression", {"mot_de_passe": "non"}).status_code == 422
    assert alice.post("/api/compte/suppression", {"mot_de_passe": PASSWORD}).status_code == 200

    game = bruno.get(f"/api/parties/{code}").data["partie"]
    assert (game["statut"], game["resultat"], game["raison"]) == ("terminee", "0-1", "abandon")
    assert game["blancs"] == {"pseudo": "Compte supprimé", "invite": False}


def test_pages_that_need_an_account(browser):
    assert browser.get("/api/parties").status_code == 401
    assert browser.post("/api/compte/mot-de-passe", {}).status_code == 401
    assert browser.get("/api/inconnu").status_code == 404
    assert browser.request("put", "/api/connexion").status_code == 405
