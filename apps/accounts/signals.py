from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, User


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, display_name=instance.get_full_name())
