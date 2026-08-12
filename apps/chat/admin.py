from django.contrib import admin

from .models import CallSession, Conversation, Message

admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(CallSession)
