from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Block, Follow, Profile, User


@admin.register(User)
class PulsoUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "created_at")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "specialty", "is_hidden", "cover_position_y", "updated_at")
    list_filter = ("is_hidden", "specialty", "is_available_for_work")
    search_fields = ("user__username", "user__email", "display_name")
    list_editable = ("is_hidden",)


admin.site.register(Follow)
admin.site.register(Block)
