"""API des parties. Toutes les actions passent ici, protégées par le jeton CSRF ; le WebSocket
sert seulement à prévenir l'adversaire qu'il y a du nouveau."""

from django.http import JsonResponse

from config.api import ApiError, api_view, read_json

from . import services
from .models import Game


@api_view("GET", "POST", login_required=True)
def games(request):
    if request.method == "GET":
        return JsonResponse(services.games_of(request.user))
    data = read_json(request)
    game = services.create_game(request.user, data.get("couleur", "hasard"))
    return JsonResponse({"partie": services.game_state(game, request.user)}, status=201)


@api_view("GET", "DELETE", login_required=True)
def game(request, code):
    if request.method == "DELETE":
        services.cancel_game(request.user, code)
        return JsonResponse({"message": "Partie annulée."})
    game = services.get_game(code)
    if game.color_of(request.user) is not None:
        return JsonResponse({"partie": services.game_state(game, request.user)})
    if game.status == Game.Status.WAITING:
        return JsonResponse({"invitation": services.invitation(game)})
    raise ApiError("Cette partie a déjà ses deux joueurs.", 403)


@api_view("POST", login_required=True)
def join(request, code):
    game = services.join_game(request.user, code)
    return JsonResponse({"partie": services.game_state(game, request.user)})


@api_view("POST", login_required=True)
def move(request, code):
    data = read_json(request)
    game = services.play_move(request.user, code, data.get("coup"), data.get("demi_coup"))
    return JsonResponse({"partie": services.game_state(game, request.user)})


@api_view("POST", login_required=True)
def resign(request, code):
    game = services.resign(request.user, code)
    return JsonResponse({"partie": services.game_state(game, request.user)})


@api_view("POST", login_required=True)
def draw(request, code):
    game = services.draw(request.user, code, read_json(request).get("action"))
    return JsonResponse({"partie": services.game_state(game, request.user)})


@api_view("POST", login_required=True)
def messages(request, code):
    message = services.post_message(request.user, code, read_json(request).get("texte"))
    return JsonResponse({"message": message.as_json()}, status=201)
