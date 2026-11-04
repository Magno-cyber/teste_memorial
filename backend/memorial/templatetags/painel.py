"""Tags do painel /administracao/."""

import hashlib
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


def _hash(caminho: str) -> str:
    arquivo = finders.find(caminho)
    if not arquivo:
        return ""
    with open(arquivo, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


_hash_guardado = lru_cache(maxsize=None)(_hash)


@register.simple_tag
def estatico(caminho: str) -> str:
    """URL do arquivo com o hash do conteúdo.

    O nginx manda o navegador guardar /static/ por 30 dias. Sem isto, quem já abriu o
    painel continua com o CSS antigo depois de uma atualização, e a página nova sai sem
    estilo. Com o hash na URL, arquivo novo é endereço novo.
    """
    versao = _hash(caminho) if settings.DEBUG else _hash_guardado(caminho)
    url = static(caminho)
    return f"{url}?v={versao}" if versao else url
