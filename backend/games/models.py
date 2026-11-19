from django.conf import settings
from django.db import models


class Game(models.Model):
    class Status(models.TextChoices):
        WAITING = "attente", "En attente d'un adversaire"
        ONGOING = "en_cours", "En cours"
        FINISHED = "terminee", "Terminée"

    class Reason(models.TextChoices):
        NONE = "", "—"
        CHECKMATE = "mat", "Échec et mat"
        STALEMATE = "pat", "Pat"
        RESIGNATION = "abandon", "Abandon"
        AGREEMENT = "accord", "Nulle par accord"
        REPETITION = "repetition", "Triple répétition"
        FIFTY_MOVES = "cinquante_coups", "Règle des cinquante coups"
        MATERIAL = "materiel", "Matériel insuffisant"

    code = models.CharField("code", max_length=8, unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_games"
    )
    white = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    black = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.WAITING)
    result = models.CharField(max_length=7, blank=True)
    reason = models.CharField(max_length=20, choices=Reason.choices, blank=True)
    # Couleur du joueur qui propose la nulle (« w » ou « b »), vide sinon.
    draw_offer = models.CharField(max_length=1, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "partie"
        indexes = [models.Index(fields=["status", "updated_at"])]

    def __str__(self) -> str:
        return self.code

    def color_of(self, user) -> str | None:
        if user is None or not user.is_authenticated:
            return None
        if self.white_id == user.pk:
            return "w"
        if self.black_id == user.pk:
            return "b"
        return None

    def player(self, color: str):
        return self.white if color == "w" else self.black


class Move(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moves")
    ply = models.PositiveSmallIntegerField("demi-coup")
    uci = models.CharField(max_length=5)
    san = models.CharField(max_length=10)
    fen = models.CharField(max_length=100)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "coup"
        ordering = ["ply"]
        constraints = [models.UniqueConstraint(fields=["game", "ply"], name="un_coup_par_demi_coup")]

    def __str__(self) -> str:
        return f"{self.game_id} : {self.san}"


class ChatMessage(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    author_name = models.CharField(max_length=20)
    text = models.CharField(max_length=300)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "message"
        ordering = ["sent_at", "pk"]

    def __str__(self) -> str:
        return f"{self.author_name} : {self.text[:40]}"

    def as_json(self) -> dict:
        return {
            "id": self.pk,
            "auteur": self.author_name,
            "auteur_id": self.author_id,
            "texte": self.text,
            "envoye_le": self.sent_at.isoformat(),
        }
