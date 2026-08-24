from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.db.models import F, Q

from apps.common.crypto import decrypt_text, encrypt_text


class User(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"@{self.username}"


class Profile(models.Model):
    class Specialty(models.TextChoices):
        PHOTO = "photography", "Fotografia"
        NAILS = "nail-art", "Nail art"
        HAIR = "hair", "Cabelo"
        PAINTING = "painting", "Pintura"
        DIGITAL = "digital-art", "Arte digital"
        FASHION = "fashion", "Moda"
        MUSIC = "music", "Música"
        DESIGN = "design", "Design"
        TATTOO = "tattoo", "Tatuagem"
        CRAFTS = "crafts", "Artesanato"
        DEVELOPMENT = "development", "Desenvolvimento"
        OTHER = "other", "Outra expressão"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.CharField(max_length=220, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    cover_position_y = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Posição vertical da capa, de 0 (topo) a 100 (base).",
    )
    is_hidden = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Perfis ocultos não aparecem em descoberta, conexões, posts ou URLs públicas.",
    )
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=300, blank=True)
    instagram_url = models.URLField(max_length=300, blank=True)
    github_url = models.URLField(max_length=300, blank=True)
    linkedin_url = models.URLField(max_length=300, blank=True)
    behance_url = models.URLField(max_length=300, blank=True)
    specialty = models.CharField(max_length=32, choices=Specialty.choices, default=Specialty.OTHER)
    pronouns = models.CharField(max_length=32, blank=True)
    is_available_for_work = models.BooleanField(default=True)
    pix_key_type = models.CharField(max_length=16, blank=True)
    pix_key_ciphertext = models.TextField(blank=True)
    pix_receiver_name = models.CharField(max_length=25, blank=True)
    pix_city = models.CharField(max_length=15, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def pix_key(self):
        return decrypt_text(self.pix_key_ciphertext)

    def set_pix_key(self, value):
        self.pix_key_ciphertext = encrypt_text(value.strip()) if value else ""

    @property
    def name(self):
        return self.display_name or self.user.get_full_name() or self.user.username

    def clean(self):
        for value in (
            self.avatar_url,
            self.cover_url,
            self.website,
            self.instagram_url,
            self.github_url,
            self.linkedin_url,
            self.behance_url,
        ):
            if value:
                URLValidator(schemes=["https"])(value)

    def __str__(self):
        return self.name


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_links")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
            models.CheckConstraint(condition=~Q(follower=F("following")), name="no_self_follow"),
        ]
        ordering = ["-created_at"]

    def clean(self):
        if self.follower_id == self.following_id:
            raise ValidationError("Você não pode seguir a si mesma.")


class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_created")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
            models.CheckConstraint(condition=~Q(blocker=F("blocked")), name="no_self_block"),
        ]
