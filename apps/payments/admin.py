from django.contrib import admin

from .models import SupportIntent


@admin.register(SupportIntent)
class SupportIntentAdmin(admin.ModelAdmin):
    list_display = ("creator", "supporter", "post", "amount", "created_at")
    search_fields = ("creator__username", "supporter__username", "message")
    readonly_fields = ("creator", "supporter", "post", "amount", "message", "created_at")
