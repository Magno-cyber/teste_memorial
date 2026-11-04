"""Grava as entradas e saídas do sistema (modelo Registro), mostradas em /administracao/.

Entrada: o que chega ao sistema (check-in, foto enviada, cadastro criado ou alterado, login).
Saída: o que deixa o sistema (cadastro ou ex-aluno removido, exportação de dados, aviso por e-mail, logout).

Privacidade: nada aqui recebe e-mail nem IP. A descrição de um ex-aluno leva nome, ano e turma, e é
apagada quando ele é removido (signals.py).
"""

from contextlib import contextmanager
from contextvars import ContextVar

from django.utils import timezone

from .models import Aluno, Registro, normalizar

SAIDAS = {
    Registro.Tipo.CADASTRO_REMOVIDO, Registro.Tipo.ALUNO_REMOVIDO, Registro.Tipo.EXPORTACAO, Registro.Tipo.AVISO_EMAIL,
    Registro.Tipo.LOGOUT,
}
SISTEMA = "Sistema"
VISITANTE = "Visitante"

_pedido = ContextVar("memorial_pedido", default=None)
_desligado = ContextVar("memorial_registro_desligado", default=False)


def texto_de_busca(descricao, autor):
    return normalizar(f"{descricao} {autor}")


def _autor_do_pedido():
    usuario = getattr(_pedido.get(), "user", None)
    return usuario.get_username() if usuario is not None and usuario.is_authenticated else SISTEMA


def desligado():
    return _desligado.get()


def registrar(tipo, descricao, *, autor=None, aluno_ref=None, em=None):
    """Cria um Registro; o autor padrão é quem fez o pedido atual (ou "Sistema", fora de um pedido)."""
    if desligado():
        return None
    descricao = descricao[:255]
    autor = (autor or _autor_do_pedido())[:150]
    campos = {"em": em} if em else {}
    return Registro.objects.create(
        tipo=tipo, descricao=descricao, autor=autor, aluno_ref=aluno_ref,
        direcao=Registro.Direcao.SAIDA if tipo in SAIDAS else Registro.Direcao.ENTRADA,
        busca=texto_de_busca(descricao, autor), **campos,
    )


def alterar_em_lote(qs, acao, **campos):
    """update() não dispara signals nem o auto_now: o registro e a versão da sala são feitos aqui.

    Sem atualizado_em, o totem não perceberia a mudança (a versão da sala vem dele).
    """
    objetos = list(qs)
    n = qs.update(atualizado_em=timezone.now(), **campos)
    for obj in objetos:
        referencia = obj.pk if isinstance(obj, Aluno) else getattr(obj, "aluno_id", None)
        registrar(Registro.Tipo.CADASTRO_ALTERADO, f"{acao}: {obj}", aluno_ref=referencia)
    return n


@contextmanager
def sem_registro():
    """Desliga o registro automático: conteúdo de exemplo, ou quem vai registrar por conta própria."""
    token = _desligado.set(True)
    try:
        yield
    finally:
        _desligado.reset(token)


class RegistroMiddleware:
    """Guarda o pedido atual, para os signals saberem quem da equipe fez a alteração."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _pedido.set(request)
        try:
            return self.get_response(request)
        finally:
            _pedido.reset(token)
