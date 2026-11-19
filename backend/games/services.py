"""Règles du site autour des parties : création, coups, abandon, nulle, messages.

Chaque action relit la partie dans une transaction, vérifie que le joueur a le droit d'agir,
puis prévient les deux joueurs par WebSocket une fois la transaction validée.
"""

import secrets

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from chess_rules import Game as ChessGame
from chess_rules import IllegalMove, square_name
from config.api import ApiError

from .models import ChatMessage, Game, Move

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I, faciles à confondre
CODE_LENGTH = 6
MAX_WAITING_GAMES = 5
MAX_MESSAGES = 5  # par joueur et par fenêtre de 10 secondes
CHAT_HISTORY = 100


def normalize_code(code: str) -> str:
    return "".join(char for char in str(code).upper() if char.isalnum())[:CODE_LENGTH]


def group_name(code: str) -> str:
    return f"partie-{code}"


def notify(code: str, event: dict) -> None:
    """Prévient les navigateurs connectés à la partie, après validation de la transaction."""
    layer = get_channel_layer()
    if layer is not None:
        transaction.on_commit(lambda: async_to_sync(layer.group_send)(group_name(code), event))


def notify_update(game: Game) -> None:
    notify(game.code, {"type": "game.update"})


# --- Lecture -----------------------------------------------------------------------------------


def get_game(code: str, *, for_update: bool = False) -> Game:
    queryset = Game.objects.select_related("white", "black", "creator")
    if for_update:
        queryset = queryset.select_for_update()
    game = queryset.filter(code=normalize_code(code)).first()
    if game is None:
        raise ApiError("Partie introuvable. Vérifiez le code.", 404)
    return game


def require_player(game: Game, user) -> str:
    color = game.color_of(user)
    if color is None:
        raise ApiError("Vous ne jouez pas dans cette partie.", 403)
    return color


def seat(game: Game, color: str) -> dict | None:
    user = game.player(color)
    if user is not None:
        return {"pseudo": user.pseudo, "invite": user.is_guest}
    if game.status == Game.Status.WAITING:
        return None
    return {"pseudo": "Compte supprimé", "invite": False}


def game_state(game: Game, user) -> dict:
    """Tout ce que le navigateur affiche pour un joueur : position, coups, coups possibles, messages."""
    moves = list(game.moves.all())
    replay = ChessGame(move.uci for move in moves)
    color = game.color_of(user)
    position = replay.position
    playing = game.status == Game.Status.ONGOING
    legal = [move.uci() for move in position.legal_moves()] if playing and color == replay.turn else []
    king = position.king_square(replay.turn)
    in_check = game.status != Game.Status.WAITING and king is not None and position.in_check()
    messages = list(game.messages.order_by("-sent_at", "-pk")[:CHAT_HISTORY])
    return {
        "code": game.code,
        "statut": game.status,
        "resultat": game.result,
        "raison": game.reason,
        "raison_texte": game.get_reason_display() if game.reason else "",
        "blancs": seat(game, "w"),
        "noirs": seat(game, "b"),
        "ma_couleur": color,
        "createur": game.creator_id == getattr(user, "pk", None),
        "fen": position.fen(),
        "trait": replay.turn,
        "coups": [{"san": move.san, "uci": move.uci} for move in moves],
        "coups_possibles": legal,
        "echec": square_name(king) if in_check else None,
        "nulle_proposee_par": game.draw_offer,
        "messages": [message.as_json() for message in reversed(messages)],
        "cree_le": game.created_at.isoformat(),
        "termine_le": game.finished_at.isoformat() if game.finished_at else None,
    }


def invitation(game: Game) -> dict:
    """Ce qu'un visiteur qui a reçu le lien voit d'une partie en attente, avant de la rejoindre."""
    free = "b" if game.white_id else "w"
    return {
        "code": game.code,
        "statut": game.status,
        "createur_pseudo": game.creator.pseudo if game.creator else "",
        "couleur_libre": free,
        "peut_rejoindre": game.status == Game.Status.WAITING,
    }


def games_of(user) -> dict:
    games = (
        Game.objects.filter(Q(white=user) | Q(black=user))
        .select_related("white", "black")
        .annotate(move_count=Count("moves"))
        .order_by("-updated_at")
    )

    def summary(game: Game) -> dict:
        color = game.color_of(user)
        opponent = game.player("b" if color == "w" else "w")
        turn = "w" if game.move_count % 2 == 0 else "b"
        return {
            "code": game.code,
            "statut": game.status,
            "resultat": game.result,
            "raison_texte": game.get_reason_display() if game.reason else "",
            "ma_couleur": color,
            "adversaire": opponent.pseudo
            if opponent
            else (None if game.status == Game.Status.WAITING else "Compte supprimé"),
            "nb_coups": game.move_count,
            "a_moi_de_jouer": game.status == Game.Status.ONGOING and turn == color,
            "maj_le": game.updated_at.isoformat(),
        }

    lists: dict[str, list] = {"en_cours": [], "en_attente": [], "terminees": []}
    for game in games:
        key = {"en_cours": "en_cours", "attente": "en_attente", "terminee": "terminees"}[game.status]
        if key != "terminees" or len(lists["terminees"]) < 30:
            lists[key].append(summary(game))
    return lists


# --- Actions -----------------------------------------------------------------------------------


def create_game(user, color: str) -> Game:
    if color not in ("w", "b", "hasard"):
        raise ApiError("Couleur inconnue.")
    if Game.objects.filter(creator=user, status=Game.Status.WAITING).count() >= MAX_WAITING_GAMES:
        raise ApiError("Vous avez déjà cinq parties en attente : annulez-en une avant d'en créer une autre.", 409)
    if color == "hasard":
        color = secrets.choice("wb")
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not Game.objects.filter(code=code).exists():
            break
    return Game.objects.create(
        code=code,
        creator=user,
        white=user if color == "w" else None,
        black=user if color == "b" else None,
    )


def join_game(user, code: str) -> Game:
    with transaction.atomic():
        game = get_game(code, for_update=True)
        if game.color_of(user) is not None:
            return game
        if game.status != Game.Status.WAITING:
            raise ApiError("Cette partie a déjà ses deux joueurs.", 409)
        if game.white_id is None:
            game.white = user
        else:
            game.black = user
        game.status = Game.Status.ONGOING
        game.save()
        notify_update(game)
    return game


def cancel_game(user, code: str) -> None:
    with transaction.atomic():
        game = get_game(code, for_update=True)
        if game.creator_id != user.pk or game.status != Game.Status.WAITING:
            raise ApiError("Seule une partie en attente peut être annulée, par la personne qui l'a créée.", 403)
        game.delete()


def finish(game: Game, result: str, reason: str) -> None:
    game.status = Game.Status.FINISHED
    game.result = result
    game.reason = reason
    game.draw_offer = ""
    game.finished_at = timezone.now()


def play_move(user, code: str, uci, ply) -> Game:
    if not isinstance(uci, str) or not isinstance(ply, int) or isinstance(ply, bool):
        raise ApiError("Coup invalide.")
    with transaction.atomic():
        game = get_game(code, for_update=True)
        color = require_player(game, user)
        if game.status != Game.Status.ONGOING:
            raise ApiError("La partie n'est pas en cours.", 409)
        played = list(game.moves.values_list("uci", flat=True))
        # Le navigateur indique sur quelle position il a joué : un coup envoyé deux fois,
        # ou sur une position déjà dépassée, est refusé au lieu d'être joué en double.
        if ply != len(played):
            raise ApiError("La position a changé entre-temps.", 409)
        replay = ChessGame(played)
        if replay.turn != color:
            raise ApiError("Ce n'est pas à vous de jouer.", 409)
        try:
            move = replay.play(uci)
        except IllegalMove as error:
            raise ApiError(str(error), 422) from error
        Move.objects.create(game=game, ply=len(played), uci=move.uci, san=move.san, fen=move.fen)
        game.draw_offer = ""
        outcome = replay.outcome()
        if outcome is not None:
            finish(game, outcome.result, outcome.reason)
        game.save()
        notify_update(game)
    return game


def resign(user, code: str) -> Game:
    with transaction.atomic():
        game = get_game(code, for_update=True)
        color = require_player(game, user)
        if game.status != Game.Status.ONGOING:
            raise ApiError("La partie n'est pas en cours.", 409)
        finish(game, "0-1" if color == "w" else "1-0", Game.Reason.RESIGNATION)
        game.save()
        notify_update(game)
    return game


def draw(user, code: str, action: str) -> Game:
    """Proposer, accepter ou refuser la nulle. Proposer quand l'adversaire l'a déjà proposée vaut accord."""
    if action not in ("proposer", "accepter", "refuser"):
        raise ApiError("Action inconnue.")
    with transaction.atomic():
        game = get_game(code, for_update=True)
        color = require_player(game, user)
        if game.status != Game.Status.ONGOING:
            raise ApiError("La partie n'est pas en cours.", 409)
        opponent = "b" if color == "w" else "w"
        if action == "proposer" and game.draw_offer == color:
            raise ApiError("Vous avez déjà proposé la nulle.", 409)
        if action in ("accepter", "refuser") and game.draw_offer != opponent:
            raise ApiError("Aucune proposition de nulle en attente.", 409)
        if action == "refuser":
            game.draw_offer = ""
        elif action == "accepter" or game.draw_offer == opponent:
            finish(game, "1/2-1/2", Game.Reason.AGREEMENT)
        else:
            game.draw_offer = color
        game.save()
        notify_update(game)
    return game


def post_message(user, code: str, text) -> ChatMessage:
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        raise ApiError("Le message est vide.")
    if len(text) > 300:
        raise ApiError("300 caractères au plus.")
    game = get_game(code)
    require_player(game, user)
    if game.status == Game.Status.WAITING:
        raise ApiError("Le chat s'ouvre quand votre adversaire a rejoint la partie.", 409)
    key = f"chat-echecs:{user.pk}"
    sent = cache.get(key, 0)
    if sent >= MAX_MESSAGES:
        raise ApiError("Vous envoyez trop de messages : patientez quelques secondes.", 429)
    cache.set(key, sent + 1, 10)
    message = ChatMessage.objects.create(game=game, author=user, author_name=user.pseudo, text=text)
    notify(game.code, {"type": "chat.message", "message": message.as_json()})
    return message


def forfeit_all(user) -> None:
    """Avant la suppression d'un compte : ses parties en cours sont perdues par abandon,
    ses parties en attente sont supprimées."""
    Game.objects.filter(creator=user, status=Game.Status.WAITING).delete()
    for game in Game.objects.filter(Q(white=user) | Q(black=user), status=Game.Status.ONGOING):
        color = game.color_of(user)
        finish(game, "0-1" if color == "w" else "1-0", Game.Reason.RESIGNATION)
        game.save()
        notify_update(game)
