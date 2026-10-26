from django.contrib import admin

# from allauth.account.decorators import secure_admin_login

from .models import Conversation, Message

# Register your models here.

# admin.autodiscover()
# admin.site.login = secure_admin_login(admin.site.login)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "created_at", "updated_at"]
    list_filter = ["user", "created_at"]
    search_fields = ["title", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content"]
    readonly_fields = ["id", "created_at"]
