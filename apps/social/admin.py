from django.contrib import admin

from .models import Bookmark, Comment, Like, Notification, Post, Repost

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Bookmark)
admin.site.register(Repost)
admin.site.register(Notification)
