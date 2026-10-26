import logging
import time

logger = logging.getLogger("chat")


class RequestLoggingMiddleware:
    """Middleware pour logger les requêtes HTTP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        # Logger la requête entrante
        logger.debug(f"→ {request.method} {request.path}")

        # Traiter la requête
        response = self.get_response(request)

        # Calculer la durée
        elapsed = time.time() - start_time

        # Logger la réponse
        logger.info(
            f"← {request.method} {request.path} "
            f"[{response.status_code}] {elapsed:.3f}s"
        )

        return response
