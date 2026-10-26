"""
Test rapide du logging.
Lancez ce script pour vérifier que le logging fonctionne.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import logging

# Récupérer les loggers
logger_chat = logging.getLogger("chat")
logger_rag = logging.getLogger("rag")

# Tester chaque niveau
logger_chat.debug("Message de debug (chat)")
logger_chat.info("Message d'info (chat)")
logger_chat.warning("Message de warning (chat)")
logger_chat.error("Message d'erreur (chat)")
logger_chat.critical("Message critique (chat)")

logger_rag.debug("Message de debug (rag)")
logger_rag.info("Message d'info (rag)")

print("✅ Logging testé. Vérifiez les fichiers dans logs/")
