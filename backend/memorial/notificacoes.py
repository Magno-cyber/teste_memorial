"""Avisa os administradores, por e-mail, de fotos e cadastros que aguardam aprovação.

O e-mail é um aviso a mais: o painel (/administracao/) mostra as pendências mesmo sem ele. Sem EMAIL_HOST
configurado nada é enviado. Uma falha no envio nunca derruba o check-in do visitante.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, get_connection
from django.db.models import Q

from .models import Aluno, Registro
from .registro import SISTEMA, registrar

log = logging.getLogger(__name__)
GRUPO_ADMINISTRATIVO = "Administrativo"


def email_configurado():
    return bool(settings.EMAIL_HOST)


def destinatarios():
    usuarios = get_user_model().objects.filter(is_active=True).exclude(email="")
    usuarios = usuarios.filter(Q(is_superuser=True) | Q(groups__name=GRUPO_ADMINISTRATIVO)).distinct()
    return sorted(set(usuarios.values_list("email", flat=True)))


def avisar_equipe(aluno, fotos, novo, url_painel):
    """Um e-mail por check-in que deixou algo pendente, com as miniaturas das fotos em anexo."""
    perfil_pendente = novo and aluno.status == Aluno.Status.PENDENTE
    if not (fotos or perfil_pendente) or not email_configurado():
        return 0
    para = destinatarios()
    if not para:
        return 0

    pendencias = []
    if fotos:
        pendencias.append(f"{len(fotos)} foto(s) para aprovar")
    if perfil_pendente:
        pendencias.append("cadastro para aprovar")
    corpo = (
        f"{aluno.nome} ({aluno.ano}, {aluno.turma}) fez check-in no Memorial: {' e '.join(pendencias)}.\n\n"
        f"Nada aparece nos totens antes da aprovação. Aprove ou recuse em:\n{url_painel}\n"
    )
    try:
        anexos = []
        for i, foto in enumerate(fotos, start=1):
            with foto.miniatura.open("rb") as arquivo:
                anexos.append((f"foto-{i}.jpg", arquivo.read(), "image/jpeg"))
        conexao = get_connection()
        mensagens = [
            EmailMessage(f"Memorial: aprovação pendente de {aluno.nome}", corpo, to=[e], attachments=anexos, connection=conexao)
            for e in para
        ]
        enviados = conexao.send_messages(mensagens) or 0
    except Exception:  # SMTP fora do ar, senha errada, destinatário recusado...
        log.exception("Aviso por e-mail não enviado (aluno nº %s).", aluno.pk)
        return 0
    registrar(
        Registro.Tipo.AVISO_EMAIL, f"Aviso de aprovação por e-mail a {enviados} pessoa(s): {aluno.nome}",
        autor=SISTEMA, aluno_ref=aluno.pk,
    )
    return enviados
