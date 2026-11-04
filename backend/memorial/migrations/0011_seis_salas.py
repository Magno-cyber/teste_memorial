"""Do percurso de 5 salas para os 6 espaços do tour.

Cada sala antiga vira o espaço de mesmo assunto, e o conteúdo já cadastrado vai junto:
1 Educação → 1 Fundação, 2 Troféus → 5 Esporte, 3 Artes → 4 Artes, 4 Professoras → 3 Professores,
5 Fechamento → 6 Alunos. A sala 2 (Diretores) é nova. Totens já configurados com ?sala=2 a 5 mudam de
espaço: confira o endereço de cada um (README).
"""

from django.db import migrations

ANTIGA_PARA_NOVA = {1: 1, 2: 5, 3: 4, 4: 3, 5: 6}
SALAS = [
    (1, "fundacao", "Fundação", "Como tudo começou, em 1958", "#8E6918", "conteudo"),
    (2, "diretores", "Diretores", "Quem conduziu a escola em cada época", "#2F62B0", "conteudo"),
    (3, "professores", "Professores", "Quem ensinou gerações de alunos", "#17805F", "conteudo"),
    (4, "artes", "Artes", "Música, teatro, dança e artes visuais", "#C43F60", "conteudo"),
    (5, "esporte", "Esporte", "Jogos, equipes e conquistas", "#B85A0C", "conteudo"),
    (6, "alunos", "Alunos", "Gerações que passaram por aqui", "#6E4BA8", "fechamento"),
]


def renumerar(apps, schema_editor):
    Sala = apps.get_model("memorial", "Sala")
    # Em duas etapas: número e slug são únicos, e a troca direta colidiria (a 3 vira 4 enquanto a 4 vira 3).
    for sala in Sala.objects.filter(numero__in=ANTIGA_PARA_NOVA):
        Sala.objects.filter(pk=sala.pk).update(
            numero=100 + ANTIGA_PARA_NOVA[sala.numero], slug=f"provisorio-{sala.pk}",
        )
    for numero, slug, nome, subtitulo, cor, tipo in SALAS:
        sala = Sala.objects.filter(numero=100 + numero).first() or Sala()
        sala.numero, sala.slug, sala.nome, sala.titulo = numero, slug, nome, nome
        sala.subtitulo, sala.cor, sala.tipo = subtitulo, cor, tipo
        sala.save()


class Migration(migrations.Migration):
    dependencies = [("memorial", "0010_tour_seis_espacos")]
    operations = [migrations.RunPython(renumerar, migrations.RunPython.noop)]
