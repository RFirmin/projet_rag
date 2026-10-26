from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.home, name="home"),
    path("new", views.new_conversation, name="new_conversation"),
    path(
        "c/<uuid:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
    path("c/<uuid:conversation_id>/ask", views.ask, name="ask"),
    path("c/<uuid:conversation_id>/ask-form/", views.ask_form, name="ask_form"),
    path("c/<uuid:conversation_id>/ask-stream/", views.ask_stream, name="ask_stream"),
]
