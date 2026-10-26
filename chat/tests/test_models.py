from django.contrib.auth.models import User
from django.test import TestCase

from chat.models import Conversation, Message


class ConversationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_create_conversation(self):
        conv = Conversation.objects.create(user=self.user)
        self.assertEqual(conv.user, self.user)
        self.assertEqual(conv.title, "")
        self.assertIsNotNone(conv.id)

    def test_conversation_str(self):
        conv1 = Conversation.objects.create(user=self.user, title="Première")
        conv2 = Conversation.objects.create(user=self.user, title="Deuxième")
        convs = list(Conversation.objects.all())
        self.assertEqual(convs[0], conv2)  # Plus récent en premier


class MessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.conv = Conversation.objects.create(user=self.user)

    def test_create_message(self):
        msg = Message.objects.create(
            conversation=self.conv, role="user", content="Test message"
        )
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Test message")

    def test_message_ordering(self):
        msg1 = Message.objects.create(
            conversation=self.conv, role="user", content="Premier"
        )
        msg2 = Message.objects.create(
            conversation=self.conv, role="assistant", content="Deuxième"
        )
        messages = list(self.conv.messages.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)
