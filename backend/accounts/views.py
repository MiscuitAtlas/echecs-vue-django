"""Comptes : inscription, connexion, compte invité, mot de passe et suppression."""

import hashlib
import re
from functools import cache as memoize

from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from config.api import ApiError, api_view, read_json, text

from .models import User

BACKEND = "django.contrib.auth.backends.ModelBackend"
PSEUDO_PATTERN = re.compile(r"^[0-9A-Za-zÀ-ÖØ-öø-ÿ_.-]{3,20}$")
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60
MAX_GUESTS_PER_HOUR = 30


@memoize
def dummy_hash() -> str:
    """Empreinte comparée quand l'email est inconnu : la réponse prend le même temps qu'avec
    un vrai compte, ce qui ne révèle pas quelles adresses sont inscrites."""
    return make_password("mot de passe qui ne correspond à aucun compte")


def session_payload(request) -> dict:
    user = request.user
    return {"utilisateur": user.as_json() if user.is_authenticated else None, "csrf": get_token(request)}


def password(data: dict, name: str) -> str:
    value = data.get(name, "")
    return value if isinstance(value, str) and len(value) <= 128 else ""


def client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "")


@ensure_csrf_cookie
@api_view("GET")
def session(request):
    return JsonResponse(session_payload(request))


@api_view("POST")
def register(request):
    data = read_json(request)
    pseudo = text(data, "pseudo", 40)
    email = text(data, "email", 254).lower()
    secret = password(data, "mot_de_passe")
    current = request.user if request.user.is_authenticated else None
    if current is not None and not current.is_guest:
        raise ApiError("Vous êtes déjà connecté.", 409)

    others = User.objects.exclude(pk=current.pk) if current else User.objects.all()
    errors = {}
    if not PSEUDO_PATTERN.match(pseudo):
        errors["pseudo"] = "De 3 à 20 caractères : lettres, chiffres, point, tiret ou tiret bas."
    elif pseudo.lower().startswith("invit"):
        errors["pseudo"] = "Ce début de pseudo est réservé aux comptes invités."
    elif others.filter(pseudo__iexact=pseudo).exists():
        errors["pseudo"] = "Ce pseudo est déjà pris."
    try:
        validate_email(email)
        if others.filter(email=email).exists():
            errors["email"] = "Un compte existe déjà avec cette adresse."
    except ValidationError:
        errors["email"] = "Adresse email invalide."
    try:
        validate_password(secret, User(pseudo=pseudo, email=email))
    except ValidationError as error:
        errors["mot_de_passe"] = " ".join(error.messages)
    if errors:
        raise ApiError("Corrigez les champs signalés.", 422, errors)

    try:
        with transaction.atomic():
            if current is not None:
                # Un invité qui crée son compte garde ses parties.
                user = current
                user.pseudo, user.email, user.is_guest = pseudo, email, False
                user.set_password(secret)
                user.save()
            else:
                user = User.objects.create_user(pseudo, email, secret)
    except IntegrityError as error:
        raise ApiError("Ce pseudo ou cette adresse vient d'être pris.", 422) from error
    login(request, user, backend=BACKEND)
    return JsonResponse(session_payload(request), status=201)


@api_view("POST")
def login_view(request):
    data = read_json(request)
    email = text(data, "email", 254).lower()
    secret = password(data, "mot_de_passe")
    key = "connexion-echecs:" + hashlib.sha256(email.encode()).hexdigest()
    failures = cache.get(key, 0)
    if failures >= MAX_FAILURES:
        raise ApiError("Trop de tentatives pour ce compte. Réessayez dans 15 minutes.", 429)

    user = User.objects.filter(email=email, is_guest=False, is_active=True).first()
    if user is None:
        check_password(secret, dummy_hash())
    if user is None or not user.check_password(secret):
        cache.set(key, failures + 1, LOCK_SECONDS)
        raise ApiError("Email ou mot de passe incorrect.", 401)

    cache.delete(key)
    guest = request.user if request.user.is_authenticated and request.user.is_guest else None
    login(request, user, backend=BACKEND)
    if guest is not None and guest.pk != user.pk:
        guest.delete()
    return JsonResponse(session_payload(request))


@api_view("POST")
def guest(request):
    if request.user.is_authenticated:
        raise ApiError("Vous êtes déjà connecté.", 409)
    key = "invites-echecs:" + client_ip(request)
    created = cache.get(key, 0)
    if created >= MAX_GUESTS_PER_HOUR:
        raise ApiError("Trop de comptes invités créés depuis cette adresse. Réessayez plus tard.", 429)
    cache.set(key, created + 1, 3600)
    user = User.objects.create_guest()
    login(request, user, backend=BACKEND)
    return JsonResponse(session_payload(request), status=201)


@api_view("POST")
def logout_view(request):
    user = request.user
    logout(request)
    # Un compte invité n'a pas de mot de passe : une fois déconnecté, personne ne peut plus s'en servir.
    if user.is_authenticated and user.is_guest:
        user.delete()
    return JsonResponse(session_payload(request))


@api_view("POST", login_required=True)
def change_password(request):
    user = request.user
    if user.is_guest:
        raise ApiError("Un compte invité n'a pas de mot de passe : créez d'abord votre compte.", 403)
    data = read_json(request)
    if not user.check_password(password(data, "actuel")):
        raise ApiError("Corrigez les champs signalés.", 422, {"actuel": "Mot de passe actuel incorrect."})
    new = password(data, "nouveau")
    try:
        validate_password(new, user)
    except ValidationError as error:
        raise ApiError("Corrigez les champs signalés.", 422, {"nouveau": " ".join(error.messages)}) from error
    user.set_password(new)
    user.save(update_fields=["password"])
    # La session en cours reste ouverte ; les autres sessions du compte sont fermées.
    update_session_auth_hash(request, user)
    return JsonResponse({"message": "Mot de passe modifié."})


@api_view("POST", login_required=True)
def delete_account(request):
    user = request.user
    if not user.is_guest and not user.check_password(password(read_json(request), "mot_de_passe")):
        raise ApiError("Corrigez les champs signalés.", 422, {"mot_de_passe": "Mot de passe incorrect."})
    logout(request)
    user.delete()
    return JsonResponse(session_payload(request))
