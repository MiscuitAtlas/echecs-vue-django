"""Parties : création, coups validés par le serveur, abandon, nulle, messages."""

import pytest

from games.models import Game


def move(browser, code, uci, ply):
    return browser.post(f"/api/parties/{code}/coups", {"coup": uci, "demi_coup": ply})


def test_create_then_join_with_the_code(browser, make_browser):
    browser.register("alice")
    created = browser.post("/api/parties", {"couleur": "b"})
    assert created.status_code == 201
    code = created.data["partie"]["code"]
    assert len(code) == 6
    assert created.data["partie"]["ma_couleur"] == "b"
    assert created.data["partie"]["blancs"] is None

    bruno = make_browser()
    bruno.register("bruno")
    invitation = bruno.get(f"/api/parties/{code.lower()}").data["invitation"]
    assert invitation == {
        "code": code,
        "statut": "attente",
        "createur_pseudo": "alice",
        "couleur_libre": "w",
        "peut_rejoindre": True,
    }

    joined = bruno.post(f"/api/parties/{code}/rejoindre").data["partie"]
    assert (joined["statut"], joined["ma_couleur"], joined["trait"]) == ("en_cours", "w", "w")
    assert len(joined["coups_possibles"]) == 20

    third = make_browser()
    third.register("chloe")
    assert third.post(f"/api/parties/{code}/rejoindre").status_code == 409
    assert third.get(f"/api/parties/{code}").status_code == 403
    assert third.get("/api/parties/ZZZZZZ").status_code == 404


def test_only_the_player_to_move_can_play_and_only_legal_moves(two_players):
    alice, bruno, code = two_players

    assert move(bruno, code, "e7e5", 0).data["erreur"] == "Ce n'est pas à vous de jouer."
    assert move(alice, code, "e2e5", 0).status_code == 422
    assert move(alice, code, "e7e5", 0).status_code == 422  # pièce de l'adversaire
    assert move(alice, code, "e2e4", 1).status_code == 409  # position dépassée

    played = move(alice, code, "e2e4", 0)

    assert played.status_code == 200
    assert played.data["partie"]["coups"] == [{"san": "e4", "uci": "e2e4"}]
    assert played.data["partie"]["coups_possibles"] == []  # aux noirs de jouer
    assert move(alice, code, "e2e4", 0).status_code == 409  # coup envoyé deux fois
    state = bruno.get(f"/api/parties/{code}").data["partie"]
    assert state["trait"] == "b"
    assert len(state["coups_possibles"]) == 20


@pytest.mark.parametrize(
    "payload", [{"coup": 42, "demi_coup": 0}, {"coup": "e2e4", "demi_coup": "0"}, {"coup": "e2e4"}]
)
def test_malformed_moves_are_refused(two_players, payload):
    alice, _, code = two_players
    assert alice.post(f"/api/parties/{code}/coups", payload).status_code == 400


def test_checkmate_finishes_the_game(two_players):
    alice, bruno, code = two_players
    for ply, (player, uci) in enumerate([(alice, "f2f3"), (bruno, "e7e5"), (alice, "g2g4"), (bruno, "d8h4")]):
        last = move(player, code, uci, ply)

    game = last.data["partie"]
    assert (game["statut"], game["resultat"], game["raison_texte"]) == ("terminee", "0-1", "Échec et mat")
    assert game["echec"] == "e1"
    assert game["coups"][-1]["san"] == "Qh4#"
    assert move(alice, code, "a2a3", 4).status_code == 409


def test_resignation(two_players):
    _alice, bruno, code = two_players

    game = bruno.post(f"/api/parties/{code}/abandon").data["partie"]

    assert (game["resultat"], game["raison"]) == ("1-0", "abandon")
    assert bruno.post(f"/api/parties/{code}/abandon").status_code == 409


def test_draw_offer_accept_and_decline(two_players):
    alice, bruno, code = two_players

    assert bruno.post(f"/api/parties/{code}/nulle", {"action": "accepter"}).status_code == 409
    offered = alice.post(f"/api/parties/{code}/nulle", {"action": "proposer"}).data["partie"]
    assert offered["nulle_proposee_par"] == "w"
    assert alice.post(f"/api/parties/{code}/nulle", {"action": "proposer"}).status_code == 409

    bruno.post(f"/api/parties/{code}/nulle", {"action": "refuser"})
    assert alice.get(f"/api/parties/{code}").data["partie"]["nulle_proposee_par"] == ""

    alice.post(f"/api/parties/{code}/nulle", {"action": "proposer"})
    move(alice, code, "e2e4", 0)  # jouer un coup retire sa proposition
    assert alice.get(f"/api/parties/{code}").data["partie"]["nulle_proposee_par"] == ""

    bruno.post(f"/api/parties/{code}/nulle", {"action": "proposer"})
    game = alice.post(f"/api/parties/{code}/nulle", {"action": "accepter"}).data["partie"]
    assert (game["resultat"], game["raison"]) == ("1/2-1/2", "accord")


def test_chat_messages_are_kept_as_plain_text(two_players, make_browser):
    alice, bruno, code = two_players

    sent = alice.post(f"/api/parties/{code}/messages", {"texte": "  <script>alert(1)</script> bonne partie  "})

    assert sent.status_code == 201
    message = bruno.get(f"/api/parties/{code}").data["partie"]["messages"][0]
    assert (message["auteur"], message["texte"]) == ("alice", "<script>alert(1)</script> bonne partie")
    assert alice.post(f"/api/parties/{code}/messages", {"texte": "   "}).status_code == 400
    assert alice.post(f"/api/parties/{code}/messages", {"texte": "x" * 301}).status_code == 400
    outsider = make_browser()
    outsider.register("chloe")
    assert outsider.post(f"/api/parties/{code}/messages", {"texte": "coucou"}).status_code == 403


def test_chat_is_rate_limited(two_players):
    alice, _, code = two_players
    statuses = [alice.post(f"/api/parties/{code}/messages", {"texte": f"message {i}"}).status_code for i in range(6)]
    assert statuses == [201] * 5 + [429]


def test_waiting_games_can_be_cancelled_by_their_creator_only(browser, make_browser):
    browser.register("alice")
    code = browser.post("/api/parties", {}).data["partie"]["code"]
    bruno = make_browser()
    bruno.register("bruno")

    assert bruno.delete(f"/api/parties/{code}").status_code == 403
    assert browser.delete(f"/api/parties/{code}").status_code == 200
    assert not Game.objects.exists()


def test_at_most_five_waiting_games(browser):
    browser.register("alice")
    statuses = [browser.post("/api/parties", {"couleur": "w"}).status_code for _ in range(6)]
    assert statuses == [201] * 5 + [409]


def test_my_games_list(two_players):
    alice, bruno, code = two_players
    alice.post("/api/parties", {"couleur": "w"})
    move(alice, code, "e2e4", 0)

    games = bruno.get("/api/parties").data
    assert [g["code"] for g in games["en_cours"]] == [code]
    assert games["en_cours"][0]["adversaire"] == "alice"
    assert games["en_cours"][0]["a_moi_de_jouer"] is True
    assert games["en_attente"] == []
    assert len(alice.get("/api/parties").data["en_attente"]) == 1
