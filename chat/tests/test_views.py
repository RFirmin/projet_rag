import json
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.test import override_settings
from django.core.cache import cache

from chat.models import Conversation


class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_home_requires_login(self):
        response = self.client.get(reverse("chat:home"))
        self.assertEqual(response.status_code, 302)  # Redirection vers login

    def test_home_after_login(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("chat:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mes conversations")

    def test_new_conversation(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("chat:new_conversation"))
        self.assertEqual(response.status_code, 302)  # Redirection
        self.assertEqual(Conversation.objects.count(), 1)

    def test_conversation_isolation(self):
        """Un utilisateur ne peut pas voir les conversations d'un autre."""
        other_user = User.objects.create_user(username="other", password="pass")
        other_conv = Conversation.objects.create(user=other_user, title="Autre")

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("chat:conversation_detail", args=[other_conv.id])
        )
        self.assertEqual(response.status_code, 404)  # Pas trouvé


class AskViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")
        self.conv = Conversation.objects.create(user=self.user, title="Test")

    def test_ask_empty_question(self):
        """Question vide → 400 + message clair."""
        response = self.client.post(
            reverse("chat:ask", args=[self.conv.id]),
            data=json.dumps({"question": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Veuillez entrer une question.")

    def test_ask_too_long_question(self):
        """Question > 1000 caractères → 400 + message clair."""
        response = self.client.post(
            reverse("chat:ask", args=[self.conv.id]),
            data=json.dumps({"question": "a" * 1001}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("trop longue", response.json()["error"])

    def test_ask_invalid_json(self):
        """JSON invalide → 400 + message clair."""
        response = self.client.post(
            reverse("chat:ask", args=[self.conv.id]),
            data='{"question": invalid}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Format de requête invalide.")

    def test_ask_requires_login(self):
        """Non connecté → redirection."""
        self.client.logout()
        response = self.client.post(
            reverse("chat:ask", args=[self.conv.id]),
            data=json.dumps({"question": "Test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_ask_other_user_conversation(self):
        """Conversation d'un autre → 404."""
        other_user = User.objects.create_user(username="other", password="pass")
        other_conv = Conversation.objects.create(user=other_user)

        response = self.client.post(
            reverse("chat:ask", args=[other_conv.id]),
            data=json.dumps({"question": "Test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class RateLimitTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")
        self.conv = Conversation.objects.create(user=self.user, title="Test")
        cache.clear()  # Nettoyer le cache avant chaque test

    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limit_ask_stream(self):
        """Après 10 requêtes, la 11e est bloquée."""
        url = reverse("chat:ask", args=[self.conv.id])

        # Faire 10 requêtes
        for i in range(10):
            response = self.client.post(url, {"question": f"Question {i}"})
            # Note : le streaming retourne 200 même si bloqué
            # car le générateur n'est pas consommé

        # La 11e devrait être bloquée
        response = self.client.post(url, {"question": "Question 11"})

        # Le streaming retourne 200 mais avec un contenu d'erreur
        # On doit vérifier le contenu
        if hasattr(response, "streaming_content"):
            content = b"".join(response.streaming_content).decode()
            self.assertIn("Trop de requêtes", content)
        else:
            self.assertEqual(response.status_code, 429)
