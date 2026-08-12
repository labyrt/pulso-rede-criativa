from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Block, Follow, Profile, User


@admin.register(User)
class PulsoUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "created_at")
    search_fields = ("username", "email", "first_name", "last_name")


admin.site.register(Profile)
admin.site.register(Follow)
admin.site.register(Block)
