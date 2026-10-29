from django.http import JsonResponse


def resposta_bloqueio(request, *args, **kwargs):
    """Resposta do django-axes quando a numérica + IP excede o limite de tentativas."""
    return JsonResponse(
        {
            "detail": "Muitas tentativas de login. Aguarde 15 minutos e tente de novo.",
            "codigo": "login_bloqueado",
        },
        status=429,
    )
