import json, logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .models import Conversation, Message
from .utils import sse_message, sse_error, sse_stream

from Rag_1_1 import RAGPipeline

# Create your views here.

# logger pour ce module
logger = logging.getLogger(__name__)

_pipeline = None


def get_pipeline():
    """Retourne l'interface unique du pipeline RAG."""
    global _pipeline
    if _pipeline is None:
        logger.info("Chargement du pipeline RAG (première fois)")
        from django.conf import settings

        _pipeline = RAGPipeline(index_path=settings.RAG_INDEX_PATH)
        logger.info(f"Pipeline RAG chargé : {len(_pipeline.resources.chunks)} chunks")
    return _pipeline


@ratelimit(key='user', rate='5/m', block=True)
@login_required
def home(request):
    """Page d'acceuil : liste des conversations"""
    logger.debug(f"Accès à home par {request.user.username}")
    conversation = Conversation.objects.filter(user=request.user)
    logger.info(f"{request.user.username} a {conversation.count()} conversations")

    return render(request, "chat/home.html", {"conversation": conversation})


@login_required
def new_conversation(request):
    """Cree une nouvelle conversation et redirige vers elle."""
    conversation = Conversation.objects.create(
        user=request.user,
        title="Nouvelle conversation",
    )
    logger.info(
        f"Nouvelle conversation créée : {conversation.id} par {request.user.username}"
    )
    return redirect("chat:conversation_detail", conversation_id=conversation.id)


@login_required
def conversation_detail(request, conversation_id):
    """Affiche une conversation et son historique"""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, user=request.user
    )
    messages = conversation.messages.all()

    logger.debug(
        f"Conversation {conversation_id} consultée par {request.user.username}"
    )

    return render(
        request,
        "chat/conversation.html",
        {"conversation": conversation, "messages": messages},
    )


@login_required
@require_POST
def ask(request, conversation_id):
    """
    Traite une question et retourne un fragment HTML.
    HTMX remplacera le contenu de la cible avec ce fragment.
    10 requêtes par minute maximum par utilisateur.
    """

    from django_ratelimit.core import is_ratelimited

    # Vérifier la limite manuellement
    if is_ratelimited(
        request=request,
        group="ask_stream",  # Identifiant du groupe de limite
        key="user",  # Limiter par utilisateur
        rate="10/m",  # 10 requêtes par minute
        method="POST",
        increment=True,  # Incrémenter le compteur
    ):
        return sse_error("Trop de requêtes. Veuillez patienter une minute.")

    # 1. Conversation
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        user=request.user,
    )

    # 2. Valider la question
    # Supporte JSON et form-data
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
            question = data.get("question", "").strip()
        except json.JSONDecodeError:
            logger.warning(f"JSON invalide reçu de {request.user.username}")
            return JsonResponse(
                {"error": "Format de requête invalide."},
                status=400,
            )
    else:
        question = request.POST.get("question", "").strip()

    # 3. Validation
    if not question:
        # return HttpResponse(
        #     '<div class="error">Veuillez entrer une question.</div>',
        #     status=400,
        # )
        return JsonResponse(
            {"error": "Veuillez entrer une question."},
            status=400,
        )

    if len(question) > 1000:
        return JsonResponse(
            {"error": "Question trop longue (max 1000 caractères)."},
            status=400,
        )
    # 4. Traiter avec gestion d'erreur
    try:
        # Sauvegarder la question
        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content=question,
        )

        # Appeler le pipeline RAG
        pipeline = get_pipeline()
        result = pipeline.ask(question)

        # Sauvegarder la reponse
        assistant_message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=result["answer"],
            sources=result.get("sources", []),
        )

        # Mettre a jour le titre si c'est le premier message
        if conversation.messages.count() == 2:
            conversation.title = question[:100]
            conversation.save()

        # Retourner un fragment HTML avec les deux messages
        html = render_to_string(
            "chat/partials/messages.html",
            {
                "messages": [user_message, assistant_message],
            },
        )

        return JsonResponse(
            {
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "html": html,
            }
        )

    except Exception as e:
        logger.exception(f"Erreur dans ask : {e}")
        return JsonResponse(
            {"error": "Une erreur est survenue. Veuillez réessayer."},
            status=500,
        )
    # return HttpResponse(html)


@login_required
def ask_form(request, conversation_id):
    """Vue de test pour ask (affiche un formulaire)."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        user=request.user,
    )

    result = None
    question = ""

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            # Appeler la logique de ask
            pipeline = get_pipeline()
            try:
                result = pipeline.ask(question)
            except Exception as e:
                logger.exception(f"Erreur dans ask_form : {e}")
                result = {"error": "Une erreur est survenue."}

    return render(
        request,
        "chat/ask_form.html",
        {
            "conversation": conversation,
            "question": question,
            "result": result,
        },
    )


@login_required
@require_POST
def ask_stream(request, conversation_id):
    """
    Version streaming de ask().
    Utilise SSE (Server-Sent Events) pour envoyer la réponse mot par mot.
    10 requêtes par minute maximum par utilisateur.
    """
    from django_ratelimit.core import is_ratelimited

    # Vérifier la limite manuellement
    if is_ratelimited(
        request=request,
        group="ask_stream",  # Identifiant du groupe de limite
        key="user",  # Limiter par utilisateur
        rate="10/m",  # 10 requêtes par minute
        method="POST",
        increment=True,  # Incrémenter le compteur
    ):
        return sse_error("Trop de requêtes. Veuillez patienter une minute.")

    # 1. Conversation
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        user=request.user,
    )

    # 2. Validation
    question = request.POST.get("question", "").strip()

    if not question:
        return sse_error("Veuiller entrer une question.")
        # logger.warning(f"Question vide de {request.user.username} dans {conversation_id}")
        # return StreamingHttpResponse(
        #     iter(["data: ❌ Question vide\n\n"]),
        #     content_type="text/event-stream",
        # )

    if len(question) > 1000:
        return sse_error("question trop longue (max 1000 caracteres).")

    logger.info(
        f"Question de {request.user.username} dans {conversation_id} : {question[:100]}"
    )

    # Sauvegarder la question
    Message.objects.create(
        conversation=conversation,
        role="user",
        content=question,
    )

    # Appeler le pipeline RAG
    pipeline = get_pipeline()

    def event_stream():
        """Générateur qui yield les événements SSE."""
        full_answer = ""

        try:
            # Message utilisateur
            yield sse_message("user", question)

            # yield f"data: {json.dumps({'type': 'user', 'content': question})}\n\n"

            # import time
            # start_time = time.time()

            # Streamer la réponse
            for chunk in pipeline.ask_stream(question):
                full_answer += chunk
                yield sse_message("chunk", chunk)

            # for chunk in pipeline.ask_stream(question):
            #     full_answer += chunk
            #     yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            #     elapsed = time.time() - start_time
            #     logger.info(f"Réponse générée en {elapsed:.2f}s pour {request.user.username} "
            #            f"({len(full_answer)} caractères)")

            # Sauvegarder la réponse complète
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=full_answer,
                sources=[],
            )

            # Mettre à jour le titre si premier échange
            if conversation.messages.count() == 2:
                conversation.title = question[:100]
                conversation.save()
                logger.debug(
                    f"Titre de {conversation.id} mis à jour : {conversation.title}"
                )

            # Signal de fin
            yield sse_message("done")
            # yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception(f"Erreur dans ask_stream : {e}")
            yield sse_message("error", "Une erreur est survenue. Veuillez réessayer.")
            # logger.exception(f"Erreur lors du streaming pour {request.user.username} : {e}")
            # yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return sse_stream(event_stream())

    # response = StreamingHttpResponse(
    #     event_stream(),
    #     content_type="text/event-stream",
    # )
    # response["Cache-Control"] = "no-cache"
    # response["X-Accel-Buffering"] = "no"

    # return response
