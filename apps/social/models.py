from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


class Post(models.Model):
    class Category(models.TextChoices):
        PHOTO = "photography", "Fotografia"
        BEAUTY = "beauty", "Beleza"
        ART = "art", "Arte"
        DESIGN = "design", "Design"
        FASHION = "fashion", "Moda"
        MUSIC = "music", "Música"
        PROCESS = "process", "Processo criativo"
        OPPORTUNITY = "opportunity", "Oportunidade"
        DEVELOPMENT = "development", "Desenvolvimento"
        OTHER = "other", "Outros"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField(validators=[MaxLengthValidator(500)])
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER)
    image_url = models.URLField(max_length=700, blank=True)
    video_url = models.URLField(max_length=700, blank=True)
    portfolio_url = models.URLField(max_length=700, blank=True)
    tags = models.CharField(max_length=240, blank=True, help_text="Tags separadas por vírgula")
    accepts_support = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "-created_at"])]

    def __str__(self):
        return f"{self.author}: {self.body[:40]}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
    body = models.CharField(max_length=350)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_like")]


class Bookmark(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_bookmark")]


class Repost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reposts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reposts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_repost")]


class Notification(models.Model):
    class Kind(models.TextChoices):
        FOLLOW = "follow", "Novo seguidor"
        LIKE = "like", "Curtida"
        COMMENT = "comment", "Comentário"
        REPOST = "repost", "Compartilhamento"
        MESSAGE = "message", "Mensagem"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]
