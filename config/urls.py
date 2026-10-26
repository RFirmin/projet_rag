"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import include, path

from django_ratelimit.exceptions import Ratelimited

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentification
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="auth/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(template_name="auth/logout.html"),
        name="logout",
    ),
    # Chat
    path("", include("chat.urls")),
    path("accounts/", include("allauth.urls")),
]


# 1. Créer la fonction qui gère l'erreur
def custom_403(request, exception):
    """Vue appelée quand la limite de requêtes est atteinte."""
    if isinstance(exception, Ratelimited):
        return HttpResponse('<h1>Doucement ! Vous avez fait trop de requêtes. Attendez un peu.</h1>', status=429)
    return HttpResponseForbidden('Forbidden')

handler403 = custom_403   
