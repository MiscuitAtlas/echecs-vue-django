import secrets
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

# Un compte invité qui n'a pas servi depuis ce délai est supprimé.
GUEST_LIFETIME = timedelta(days=2)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, pseudo: str, email: str | None, password: str | None = None, **extra):
        user = self.model(pseudo=pseudo, email=self.normalize_email(email).lower() if email else None, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, pseudo: str, email: str, password: str, **extra):
        return self.create_user(pseudo, email, password, is_staff=True, **extra)

    def create_guest(self):
        """Compte invité, sans email ni mot de passe : il ne vit que dans la session du navigateur."""
        self.purge_guests()
        while True:
            pseudo = f"Invité-{secrets.randbelow(9000) + 1000}"
            if not self.filter(pseudo__iexact=pseudo).exists():
                return self.create_user(pseudo, None, None, is_guest=True)

    def purge_guests(self) -> int:
        limit = timezone.now() - GUEST_LIFETIME
        stale = self.filter(is_guest=True, date_joined__lt=limit).exclude(last_login__gte=limit)
        return stale.delete()[0]


class User(AbstractBaseUser):
    pseudo = models.CharField("pseudo", max_length=20, unique=True)
    email = models.EmailField("adresse email", max_length=254, unique=True, null=True, blank=True)
    is_guest = models.BooleanField("invité", default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField("inscrit le", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "pseudo"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "joueur"
        constraints = [models.UniqueConstraint(Lower("pseudo"), name="pseudo_unique_sans_casse")]

    def __str__(self) -> str:
        return self.pseudo

    def as_json(self) -> dict:
        return {"id": self.pk, "pseudo": self.pseudo, "email": self.email, "invite": self.is_guest}
