"""
Gestion de la mémoire conversationnelle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Message:
    """Un message dans la conversation."""

    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: Optional[List[Dict]] = None

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
        }


class ConversationMemory:
    """
    Gère l'historique d'une conversation.

    Usage :
        memory = ConversationMemory(max_turns=5)
        memory.add_user("Qu'est-ce qu'une liste ?")
        memory.add_assistant("Une liste est...")
        context = memory.get_context()
    """

    def __init__(self, max_turns: int = 5):
        """
        Args:
            max_turns: Nombre maximum de tours (1 tour = 1 question + 1 réponse)
        """
        self.max_turns = max_turns
        self.messages: List[Message] = []

    def add_user(self, content: str) -> None:
        """Ajoute un message utilisateur."""
        self.messages.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str, sources: List[Dict] = None) -> None:
        """Ajoute une réponse de l'assistant."""
        self.messages.append(
            Message(
                role="assistant",
                content=content,
                sources=sources,
            )
        )
        self._trim()

    def _trim(self) -> None:
        """Garde seulement les max_turns derniers tours."""
        max_messages = self.max_turns * 2  # user + assistant par tour
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

    def get_context(self) -> str:
        """
        Retourne l'historique formaté pour le LLM.

        Format :
            Utilisateur: ...
            Assistant: ...
            Utilisateur: ...
        """
        if not self.messages:
            return ""

        lines = []
        for msg in self.messages:
            role_label = "Utilisateur" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")

        return "\n\n".join(lines)

    def get_messages(self) -> List[Dict]:
        """Retourne les messages au format OpenAI/Groq."""
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """Vide l'historique."""
        self.messages = []

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return f"ConversationMemory({len(self.messages)} messages, max_turns={self.max_turns})"
