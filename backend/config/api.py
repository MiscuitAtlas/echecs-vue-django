"""Outils communs aux vues de l'API JSON."""

import json
from functools import wraps

from django.http import JsonResponse


class ApiError(Exception):
    """Erreur renvoyée telle quelle au navigateur : message en français, code HTTP, erreurs par champ."""

    def __init__(self, message: str, status: int = 400, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.fields = fields or {}


def read_json(request) -> dict:
    if request.content_type != "application/json":
        raise ApiError("Le corps de la requête doit être en JSON.", 415)
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ApiError("JSON invalide.") from error
    if not isinstance(data, dict):
        raise ApiError("JSON invalide.")
    return data


def text(data: dict, name: str, max_length: int = 200) -> str:
    """Champ texte du JSON, toujours une chaîne (un nombre ou une liste envoyés à la place sont ignorés)."""
    value = data.get(name, "")
    return value.strip()[:max_length] if isinstance(value, str) else ""


def api_view(*methods: str, login_required: bool = False):
    """Vue JSON : méthodes autorisées, connexion exigée si besoin, ApiError transformée en réponse."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                response = JsonResponse({"erreur": "Méthode non autorisée."}, status=405)
                response["Allow"] = ", ".join(methods)
                return response
            if login_required and not request.user.is_authenticated:
                return JsonResponse({"erreur": "Connectez-vous pour continuer."}, status=401)
            try:
                return view(request, *args, **kwargs)
            except ApiError as error:
                body = {"erreur": error.message}
                if error.fields:
                    body["champs"] = error.fields
                return JsonResponse(body, status=error.status)

        return wrapper

    return decorator
