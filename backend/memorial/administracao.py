"""Painel da administração (/administracao/): todas as entradas e saídas do sistema, só para leitura.

Fora das salas e do service worker do totem. Usa o login do admin do Django: precisa de usuário da
equipe (is_staff) com a permissão memorial.view_registro (o grupo "Administrativo" já a tem).
"""

import csv
from datetime import date
from functools import wraps

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import Aluno, FotoAluno, Registro, normalizar
from .registro import registrar

POR_PAGINA = 50


def _exige_acesso(view):
    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.user.has_perm("memorial.view_registro"):
            return HttpResponseForbidden(
                "Seu usuário não tem acesso às entradas e saídas. Peça à equipe para incluí-lo no grupo Administrativo.",
                content_type="text/plain; charset=utf-8",
            )
        return view(request, *args, **kwargs)

    return require_GET(never_cache(staff_member_required(interna)))


def _data(valor):
    try:
        return date.fromisoformat(valor or "")
    except ValueError:
        return None


def _ler_filtros(parametros):
    """Valores inválidos na URL são ignorados, em vez de virar erro."""
    direcao = parametros.get("direcao", "")
    tipo = parametros.get("tipo", "")
    return {
        "q": parametros.get("q", "").strip(),
        "direcao": direcao if direcao in Registro.Direcao.values else "",
        "tipo": tipo if tipo in Registro.Tipo.values else "",
        "de": _data(parametros.get("de")),
        "ate": _data(parametros.get("ate")),
    }


def _sem_direcao(f):
    """Tudo que os filtros pedem, menos a direção: base da contagem de cada botão."""
    qs = Registro.objects.all()
    for palavra in normalizar(f["q"]).split():
        qs = qs.filter(busca__contains=palavra)
    if f["tipo"]:
        qs = qs.filter(tipo=f["tipo"])
    if f["de"]:
        qs = qs.filter(em__date__gte=f["de"])
    if f["ate"]:
        qs = qs.filter(em__date__lte=f["ate"])
    return qs


def _aplicar(f):
    qs = _sem_direcao(f)
    return qs.filter(direcao=f["direcao"]) if f["direcao"] else qs


@_exige_acesso
def painel(request):
    f = _ler_filtros(request.GET)
    contagem = _sem_direcao(f).aggregate(
        todas=Count("id"),
        entradas=Count("id", filter=Q(direcao=Registro.Direcao.ENTRADA)),
        saidas=Count("id", filter=Q(direcao=Registro.Direcao.SAIDA)),
    )
    hoje = Registro.objects.filter(em__date=timezone.localdate()).aggregate(
        entradas=Count("id", filter=Q(direcao=Registro.Direcao.ENTRADA)),
        saidas=Count("id", filter=Q(direcao=Registro.Direcao.SAIDA)),
    )
    pagina = Paginator(_aplicar(f), POR_PAGINA).get_page(request.GET.get("pagina"))
    return render(request, "memorial/administracao.html", {
        "filtros": f,
        "contagem": contagem,
        "hoje": hoje,
        "checkins": Aluno.objects.filter(origem=Aluno.Origem.CHECKIN, demonstrativo=False).count(),
        "fotos_pendentes": FotoAluno.objects.filter(status=FotoAluno.Status.PENDENTE, aluno__demonstrativo=False).count(),
        "perfis_pendentes": Aluno.objects.filter(status=Aluno.Status.PENDENTE, demonstrativo=False).count(),
        "pode_moderar": request.user.has_perm("memorial.change_fotoaluno"),
        "pagina": pagina,
        "tipos": Registro.Tipo.choices,
        "tem_filtro": any(f.values()),
    })


def _celula(valor):
    """Nomes vêm do público: uma célula que começa com = + - @ viraria fórmula no Excel."""
    texto = str(valor)
    return f"'{texto}" if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


@_exige_acesso
def exportar(request):
    f = _ler_filtros(request.GET)
    registros = _aplicar(f)
    total = registros.count()
    linhas = list(registros)  # antes de registrar: a própria exportação não entra no arquivo
    registrar(Registro.Tipo.EXPORTACAO, f"Exportação em CSV de {total} registro(s)")

    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = f'attachment; filename="entradas-e-saidas-{timezone.localdate().isoformat()}.csv"'
    resposta.write("﻿")  # o Excel só reconhece os acentos com este marcador
    saida = csv.writer(resposta, delimiter=";")
    saida.writerow(["Data e hora", "Direção", "Tipo", "Descrição", "Quem"])
    for r in linhas:
        saida.writerow([
            timezone.localtime(r.em).strftime("%d/%m/%Y %H:%M:%S"), r.get_direcao_display(), r.get_tipo_display(),
            _celula(r.descricao), _celula(r.autor),
        ])
    return resposta
