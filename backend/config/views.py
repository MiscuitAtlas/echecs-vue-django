"""Pages hors API : l'application Vue, et les réponses d'erreur au format JSON."""

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse


def frontend(request, path=""):
    """Toutes les adresses de l'application Vue renvoient sa page unique ; le routeur Vue fait le reste."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Interface non construite : lancez « npm run build » dans frontend/, "
            "ou utilisez le serveur de développement Vite.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    response = FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response


def api_not_found(request, path=""):
    return JsonResponse({"erreur": "Adresse d'API inconnue."}, status=404)


def csrf_failure(request, reason=""):
    return JsonResponse({"erreur": "Session expirée : rechargez la page et recommencez."}, status=403)
