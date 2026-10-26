import json
from django.http import StreamingHttpResponse


def sse_message(msg_type: str, content: str = None, **kwargs) -> str:
    """Formate un message SSE."""
    data = {"type": msg_type}
    if content is not None:
        data["content"] = content
    data.update(kwargs)
    return f"data: {json.dumps(data)}\n\n"


def sse_error(message: str) -> StreamingHttpResponse:
    """Retourne une erreur au format SSE."""
    return StreamingHttpResponse(
        iter([sse_message("error", message)]),
        content_type="text/event-stream",
    )


def sse_stream(generator) -> StreamingHttpResponse:
    """Enveloppe un generateur dans une reponse SSE."""
    response = StreamingHttpResponse(
        generator,
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
