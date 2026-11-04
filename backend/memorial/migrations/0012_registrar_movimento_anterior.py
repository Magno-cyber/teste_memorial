"""Leva para o Registro os check-ins e fotos que já existiam antes dele.

O que a equipe fez antes (alterações, logins) não foi guardado aqui; o histórico do admin do Django
continua na página de cada item. Conteúdo de exemplo fica de fora, como no carregar_exemplo.
"""

from django.db import migrations

from memorial.models import normalizar


def preencher(apps, schema_editor):
    Aluno = apps.get_model("memorial", "Aluno")
    FotoAluno = apps.get_model("memorial", "FotoAluno")
    Registro = apps.get_model("memorial", "Registro")

    def novo(tipo, em, descricao, autor, aluno_ref):
        return Registro(
            em=em, tipo=tipo, direcao="entrada", descricao=descricao[:255], autor=autor, aluno_ref=aluno_ref,
            busca=normalizar(f"{descricao} {autor}"),
        )

    registros = []
    for a in Aluno.objects.filter(demonstrativo=False):
        identificacao = f"{a.nome} ({a.ano}, {a.turma})"
        if a.origem == "checkin":
            registros.append(novo("checkin_novo", a.checkin_em, f"Check-in: {identificacao}", "Visitante", a.pk))
        else:
            registros.append(novo("cadastro_criado", a.criado_em, f"Ex-aluno: {identificacao}", "Equipe", a.pk))
    for f in FotoAluno.objects.filter(aluno__demonstrativo=False).select_related("aluno"):
        registros.append(novo("foto_enviada", f.criado_em, f"Foto enviada por {f.aluno.nome}", "Visitante", f.aluno_id))
    Registro.objects.bulk_create(registros, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("memorial", "0011_seis_salas")]
    operations = [migrations.RunPython(preencher, migrations.RunPython.noop)]
