"""Testes da API do Memorial: busca, privacidade, check-in e versão por sala.

    python manage.py test memorial
"""

import json
import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from .registro import registrar

from .administracao import _celula
from .models import (
    Acontecimento, Aluno, Apresentacao, ConfiguracaoMemorial, Decada, Foto, FotoAluno, Marco, Registro, Sala, Video,
    chave_turma, normalizar,
)

from django.conf import settings

MEDIA = tempfile.mkdtemp(prefix="memorial-testes-")
CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def limites(minuto, hora="1000/hour"):
    return {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"checkin_minuto": minuto, "checkin_hora": hora}}
EMAIL = "pessoa.real@exemplo.com"


def png(tamanho=(40, 30), formato="PNG", exif=False):
    buf = BytesIO()
    img = Image.new("RGB", tamanho, (120, 90, 60))
    extra = {}
    if exif:
        e = Image.Exif()
        e[0x010F] = "CameraSecreta"  # Make
        extra["exif"] = e.tobytes()
    img.save(buf, formato, **extra)
    return SimpleUploadedFile(f"foto.{formato.lower()}", buf.getvalue(), content_type=f"image/{formato.lower()}")


def aluno(nome, ano=1998, turma="3º A", **kw):
    dados = {"consentimento": True, "status": Aluno.Status.APROVADO, "email": f"{normalizar(nome).replace(' ', '.')}@x.com"}
    dados.update(kw)
    return Aluno.objects.create(nome=nome, ano=ano, turma=turma, **dados)


@override_settings(MEDIA_ROOT=MEDIA, CACHES=CACHE, REST_FRAMEWORK=limites("1000/min"))
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def get(self, url, **params):
        r = self.client.get(url, params)
        self.assertNotIn(b"@", r.content.replace(b"@x.com", b"!"), "resposta contém algo parecido com e-mail")
        return r

    def checkin(self, **dados):
        base = {"nome": "Maria Clara Souza", "ano": "1998", "turma": "3º A", "email": EMAIL,
                "instagram": "", "facebook": "", "consentimento": "true", "site": ""}
        base.update(dados)
        return self.client.post("/api/memorial/checkin/", base)


class BuscaTests(Base):
    def setUp(self):
        super().setUp()
        aluno("João Pedro da Silva Sales", 2007, "2º B")
        aluno("Ana Beatriz Silva Moura", 1998)
        aluno("Antônio Silva Façanha", 1962, "4ª série")
        aluno("Beatriz Coelho Lima", 1992, "8ª A")

    def nomes(self, **params):
        return [a["nome"] for a in self.get("/api/memorial/alunos/", **params).json()["resultados"]]

    def test_sem_acento_e_por_parte_do_nome(self):
        self.assertEqual(self.nomes(q="joao sil"), ["João Pedro da Silva Sales"])
        self.assertEqual(self.nomes(q="JOÃO   SILVA"), ["João Pedro da Silva Sales"])
        self.assertEqual(self.nomes(q="facanha"), ["Antônio Silva Façanha"])
        self.assertEqual(self.nomes(q="antonio"), ["Antônio Silva Façanha"])

    def test_cada_palavra_precisa_estar_no_nome(self):
        self.assertEqual(self.nomes(q="silva beatriz"), ["Ana Beatriz Silva Moura"])
        self.assertEqual(self.nomes(q="joao moura"), [])

    def test_ano_e_decada(self):
        self.assertEqual(self.nomes(ano=1962), ["Antônio Silva Façanha"])
        self.assertEqual(sorted(self.nomes(decada="1990-1999")), ["Ana Beatriz Silva Moura", "Beatriz Coelho Lima"])
        self.assertEqual(self.nomes(decada="1958–1969"), ["Antônio Silva Façanha"])
        self.assertEqual(self.nomes(q="beatriz", decada="1990-1999", ano=1992), ["Beatriz Coelho Lima"])

    def test_anos_do_diretorio_e_paginacao(self):
        for i in range(20):
            aluno(f"Pessoa Teste {i:02d}", 2010)
        r = self.get("/api/memorial/alunos/").json()
        self.assertEqual(r["anos"], [1962, 1992, 1998, 2007, 2010])
        self.assertEqual((r["total"], r["paginas"], len(r["resultados"])), (24, 2, 12))
        r2 = self.get("/api/memorial/alunos/", pagina=2).json()
        self.assertEqual(len(r2["resultados"]), 12)
        self.assertFalse({a["id"] for a in r["resultados"]} & {a["id"] for a in r2["resultados"]})

    def test_recentes_primeiro_com_selo_novo(self):
        Aluno.objects.update(checkin_em=timezone.now() - timedelta(days=5))
        novo = aluno("Zé Recém Chegado", 2001)
        r = self.get("/api/memorial/alunos/").json()["resultados"]
        self.assertEqual(r[0]["id"], novo.pk)
        self.assertTrue(r[0]["novo"])
        self.assertFalse(any(a["novo"] for a in r[1:]))
        self.assertEqual([a["nome"] for a in r[1:]], sorted([a["nome"] for a in r[1:]], key=normalizar))


class PrivacidadeTests(Base):
    def setUp(self):
        super().setUp()
        self.visivel = aluno("Ana Visível Silva", turma="3º A", instagram="ana.v")
        self.pendente = aluno("Bruno Pendente Silva", status=Aluno.Status.PENDENTE)
        self.oculto = aluno("Carla Oculta Silva", status=Aluno.Status.OCULTO)
        self.sem_consentimento = aluno("Davi Sem Termo Silva", consentimento=False)
        self.colega = aluno("Eva Colega Silva", turma="3o a")
        FotoAluno.objects.create(aluno=self.visivel, imagem=png(), legenda="aprovada", status=FotoAluno.Status.APROVADA)
        FotoAluno.objects.create(aluno=self.visivel, imagem=png(), legenda="pendente")
        FotoAluno.objects.create(aluno=self.visivel, imagem=png(), legenda="recusada", status=FotoAluno.Status.RECUSADA)

    def test_so_aprovados_com_consentimento_na_lista(self):
        r = self.get("/api/memorial/alunos/", q="silva").json()
        self.assertEqual({a["nome"] for a in r["resultados"]}, {"Ana Visível Silva", "Eva Colega Silva"})

    def test_perfis_invisiveis_dao_404(self):
        for a in (self.pendente, self.oculto, self.sem_consentimento):
            self.assertEqual(self.get(f"/api/memorial/alunos/{a.pk}/").status_code, 404)

    def test_perfil_sem_email_e_so_fotos_aprovadas(self):
        r = self.get(f"/api/memorial/alunos/{self.visivel.pk}/")
        corpo = r.content.decode()
        for proibido in ("email", "@x.com", "consentimento", "pessoa.real"):
            self.assertNotIn(proibido, corpo)
        p = r.json()
        self.assertEqual([f["legenda"] for f in p["fotos"]], ["aprovada"])
        self.assertEqual(p["instagram"], "ana.v")
        # "3o a" e "3º A" são a mesma turma; os invisíveis da mesma turma ficam de fora
        self.assertEqual([c["nome"] for c in p["colegas"]], ["Eva Colega Silva"])

    def test_nenhuma_resposta_tem_email(self):
        with open("/dev/null", "w") as nada:
            call_command("carregar_exemplo", stdout=nada)
        self.checkin()
        urls = ["/api/memorial/alunos/", "/api/memorial/checkin/", "/api/memorial/versao/?sala=5"]
        urls += [f"/api/memorial/sala/{n}/" for n in range(1, 6)]
        urls += [f"/api/memorial/alunos/{a.pk}/" for a in Aluno.objects.filter(status="aprovado", consentimento=True)]
        for url in urls:
            corpo = self.client.get(url).content.decode()
            self.assertNotIn(EMAIL, corpo, url)
            self.assertNotIn('"email"', corpo, url)
            self.assertNotIn("@x.com", corpo, url)


class CheckinTests(Base):
    def test_cria_e_aparece_na_sala_5(self):
        r = self.checkin(instagram="@maria.souza")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"ok": True})  # sem eco de dados
        a = Aluno.objects.get()
        self.assertEqual((a.nome, a.ano, a.turma, a.instagram, a.status), ("Maria Clara Souza", 1998, "3º A", "maria.souza", "aprovado"))
        self.assertEqual(a.consentimento_versao, ConfiguracaoMemorial.atual().termo_versao)
        self.assertEqual(self.get("/api/memorial/alunos/", q="maria clara").json()["total"], 1)

    def test_mesmo_email_e_ano_atualiza(self):
        self.checkin()
        r = self.checkin(nome="Maria Clara Souza Lima", turma="3º B", email=EMAIL.upper())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Aluno.objects.count(), 1)
        self.assertEqual(Aluno.objects.get().nome, "Maria Clara Souza Lima")
        self.checkin(ano="1999")
        self.assertEqual(Aluno.objects.count(), 2)

    def test_perfil_oculto_continua_oculto(self):
        self.checkin()
        Aluno.objects.update(status=Aluno.Status.OCULTO)
        self.checkin()
        self.assertEqual(Aluno.objects.get().status, Aluno.Status.OCULTO)

    def test_aprovar_perfis_deixa_pendente(self):
        c = ConfiguracaoMemorial.atual()
        c.aprovar_perfis = True
        c.save()
        self.checkin()
        self.assertEqual(Aluno.objects.get().status, Aluno.Status.PENDENTE)
        self.assertEqual(self.get("/api/memorial/alunos/").json()["total"], 0)

    def test_validacoes_com_as_mensagens_do_prototipo(self):
        casos = {
            "nome": ({"nome": "Maria"}, "Escreva nome e sobrenome."),
            "ano": ({"ano": ""}, "Escolha o ano em que estudou."),
            "turma": ({"turma": "  "}, "Informe a turma, por exemplo 3º A."),
        }
        for campo, (dados, msg) in casos.items():
            r = self.checkin(**dados)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["erros"][campo], msg)
        self.assertEqual(self.checkin(ano="1957").status_code, 400)
        self.assertEqual(self.checkin(ano=str(timezone.localdate().year + 1)).status_code, 400)
        self.assertIn("email", self.checkin(email="nao-e-email").json()["erros"])
        self.assertIn("consentimento", self.checkin(consentimento="false").json()["erros"])
        self.assertIn("instagram", self.checkin(instagram="com espaço").json()["erros"])
        self.assertEqual(Aluno.objects.count(), 0)

    def test_campo_isca_finge_sucesso_e_nao_grava(self):
        r = self.checkin(site="http://spam.example")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Aluno.objects.count(), 0)

    def test_fotos_reencodadas_sem_exif_e_pendentes(self):
        r = self.checkin(fotos=[png((3000, 2000), "JPEG", exif=True), png()])
        self.assertEqual(r.status_code, 201)
        fotos = list(FotoAluno.objects.all())
        self.assertEqual(len(fotos), 2)
        self.assertTrue(all(f.status == FotoAluno.Status.PENDENTE for f in fotos))
        grande = max(fotos, key=lambda f: f.largura)
        self.assertEqual((grande.largura, grande.altura), (2560, 1707))
        with Image.open(grande.imagem.path) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(len(img.getexif()), 0)
        # pendente: não aparece no perfil
        a = Aluno.objects.get()
        self.assertEqual(self.get(f"/api/memorial/alunos/{a.pk}/").json()["fotos"], [])

    def test_upload_invalido_recusado(self):
        falso = SimpleUploadedFile("foto.jpg", b"isto nao e uma imagem", content_type="image/jpeg")
        gif = png(formato="GIF")
        for arquivo in (falso, gif):
            r = self.checkin(fotos=[arquivo])
            self.assertEqual(r.status_code, 400)
            self.assertIn("fotos", r.json()["erros"])
        r = self.checkin(fotos=[png(), png(), png(), png()])
        self.assertEqual(r.json()["erros"]["fotos"], "Envie no máximo 3 fotos.")
        grande = SimpleUploadedFile("g.jpg", b"0" * (10 * 1024 * 1024 + 1), content_type="image/jpeg")
        self.assertEqual(self.checkin(fotos=[grande]).json()["erros"]["fotos"], "Cada foto pode ter até 10 MB.")
        self.assertEqual(Aluno.objects.count(), 0)
        self.assertEqual(FotoAluno.objects.count(), 0)

    @override_settings(REST_FRAMEWORK=limites("5/min", "30/hour"))
    def test_limite_de_frequencia(self):
        for i in range(5):
            self.assertEqual(self.checkin(email=f"p{i}@exemplo.com").status_code, 201)
        r = self.checkin(email="p6@exemplo.com")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(Aluno.objects.count(), 5)
        # ler a configuração do formulário não é limitado
        self.assertEqual(self.client.get("/api/memorial/checkin/").status_code, 200)

    def test_configuracao_do_formulario(self):
        r = self.client.get("/api/memorial/checkin/").json()
        self.assertEqual(r["anoInicial"], 1958)
        self.assertEqual(r["termoVersao"], "1.0")
        self.assertIn("Autorizo", r["termoTexto"])


class SalaTests(Base):
    def setUp(self):
        super().setUp()
        self.s1 = Sala.objects.get(numero=1)
        self.s2 = Sala.objects.get(numero=2)
        Marco.objects.create(sala=self.s1, ano=1958, titulo="A", descricao="a", destaque=True)
        Marco.objects.create(sala=self.s1, ano=1970, titulo="B", descricao="b", destaque=True)
        Foto.objects.create(sala=self.s1, ano=1960, legenda="Com imagem", imagem=png())
        Foto.objects.create(sala=self.s1, ano=1961, legenda="Rascunho", publicado=False)

    def test_sala_traz_tudo_com_urls_relativas(self):
        r = self.get("/api/memorial/sala/1/").json()
        self.assertEqual(r["sala"]["nome"], "Fundação")
        self.assertEqual(r["config"]["anoInicial"], 1958)
        self.assertEqual([m["titulo"] for m in r["marcos"]], ["A", "B"])
        self.assertEqual([m["destaque"] for m in r["marcos"]], [False, True])  # um destaque por sala
        self.assertEqual(len(r["fotos"]), 1)
        self.assertTrue(r["fotos"][0]["src"].startswith("/media/fotos/exibicao/"))
        self.assertFalse(r["demonstrativo"])

    def test_sala_inexistente_ou_inativa(self):
        self.assertEqual(self.client.get("/api/memorial/sala/9/").status_code, 404)
        Sala.objects.filter(numero=3).update(ativa=False)
        self.assertEqual(self.client.get("/api/memorial/sala/3/").status_code, 404)

    def test_versao_muda_so_com_a_propria_sala(self):
        v1 = self.get("/api/memorial/versao/", sala=1).json()["versao"]
        v2 = self.get("/api/memorial/versao/", sala=2).json()["versao"]
        Marco.objects.create(sala=self.s2, ano=1990, titulo="C", descricao="c")
        self.assertEqual(self.get("/api/memorial/versao/", sala=1).json()["versao"], v1)
        self.assertNotEqual(self.get("/api/memorial/versao/", sala=2).json()["versao"], v2)
        Foto.objects.filter(sala=self.s1).first().delete()
        self.assertNotEqual(self.get("/api/memorial/versao/", sala=1).json()["versao"], v1)
        self.assertEqual(self.client.get("/api/memorial/versao/").status_code, 400)


class ExemploTests(Base):
    def test_carregar_e_remover(self):
        real = aluno("Pessoa Real Silva")
        with open("/dev/null", "w") as nada:
            call_command("carregar_exemplo", stdout=nada)
            self.assertEqual(Marco.objects.count(), 24)  # 4 por espaço
            self.assertEqual(Apresentacao.objects.count(), 6)
            self.assertEqual(Decada.objects.count(), 42)  # 7 por espaço
            self.assertEqual(Acontecimento.objects.count(), 126)
            self.assertEqual(Registro.objects.exclude(aluno_ref=real.pk).count(), 0)  # exemplo não é movimento real
            self.assertEqual(Aluno.objects.filter(demonstrativo=True).count(), 22)
            r = self.get("/api/memorial/sala/1/").json()
            self.assertTrue(r["demonstrativo"])
            self.assertGreater(len(r["fotos"]), 100)
            self.assertEqual(len(r["decadas"]), 7)
            self.assertEqual(len(r["decadas"][0]["acontecimentos"]), 3)
            self.assertEqual(len(r["marcos"]), 4)
            self.assertTrue(r["marcos"][0]["texto"])
            self.assertGreater(len(r["apresentacao"]["texto"]), 0)
            sala6 = self.get("/api/memorial/sala/6/").json()
            self.assertEqual(sala6["sala"]["tipo"], "fechamento")
            self.assertEqual(len(sala6["decadas"]), 7)
            self.assertEqual(self.get("/api/memorial/alunos/", q="joao sil").json()["resultados"][0]["nome"],
                             "João Pedro da Silva Sales")
            call_command("carregar_exemplo", "--remover", stdout=nada)
        self.assertEqual(Marco.objects.count() + Foto.objects.count() + Decada.objects.count() + Apresentacao.objects.count(), 0)
        self.assertEqual(list(Aluno.objects.all()), [real])


class SeisEspacosTests(Base):
    def test_salas_iguais_as_do_frontend(self):
        salas = list(Sala.objects.values_list("numero", "slug", "cor", "tipo"))
        self.assertEqual(salas, [
            (1, "fundacao", "#8E6918", "conteudo"), (2, "diretores", "#2F62B0", "conteudo"),
            (3, "professores", "#17805F", "conteudo"), (4, "artes", "#C43F60", "conteudo"),
            (5, "esporte", "#B85A0C", "conteudo"), (6, "alunos", "#6E4BA8", "fechamento"),
        ])

    def test_apresentacao_decadas_e_marco_no_contrato(self):
        sala = Sala.objects.get(numero=6)
        Apresentacao.objects.create(sala=sala, titulo="Abertura", texto="Um.\n\n  Dois.\n", foto=png(), legenda="L", icone="home")
        d = Decada.objects.create(sala=sala, rotulo="Anos 60", periodo="1958 a 1969", titulo="T", resumo="R", icone="cap", foto=png())
        Acontecimento.objects.create(decada=d, ano=1958, texto="Segundo", ordem=2)
        Acontecimento.objects.create(decada=d, ano=1960, texto="Primeiro", ordem=1)
        Decada.objects.create(sala=sala, rotulo="Oculta", periodo="x", titulo="x", publicado=False)
        Marco.objects.create(sala=sala, ano=1958, titulo="M", descricao="d", texto="longo", foto=png())
        r = self.get("/api/memorial/sala/6/").json()
        self.assertEqual(r["apresentacao"]["texto"], ["Um.", "Dois."])
        self.assertTrue(r["apresentacao"]["foto"].startswith("/media/fotos/epoca/"))  # /media/fotos/ fica no cache offline
        self.assertEqual(len(r["decadas"]), 1)
        self.assertEqual([e["texto"] for e in r["decadas"][0]["acontecimentos"]], ["Primeiro", "Segundo"])
        self.assertEqual(r["marcos"][0]["texto"], "longo")
        self.assertTrue(r["marcos"][0]["foto"].endswith(".jpg"))

    def test_sala_sem_conteudo_novo_deixa_o_app_derivar(self):
        r = self.get("/api/memorial/sala/2/").json()
        self.assertIsNone(r["apresentacao"])
        self.assertEqual(r["decadas"], [])

    def test_versao_muda_com_decada_e_acontecimento(self):
        sala = Sala.objects.get(numero=1)
        versao = lambda: self.get("/api/memorial/versao/", sala=1).json()["versao"]  # noqa: E731
        v = versao()
        d = Decada.objects.create(sala=sala, rotulo="A", periodo="B", titulo="C")
        v2 = versao()
        self.assertNotEqual(v, v2)
        e = Acontecimento.objects.create(decada=d, ano=1960, texto="x")
        v3 = versao()
        self.assertNotEqual(v2, v3)
        e.delete()
        self.assertNotEqual(v3, versao())

    def test_sala_6_mostra_selo_com_conteudo_de_exemplo(self):
        sala = Sala.objects.get(numero=6)
        self.assertFalse(self.get("/api/memorial/sala/6/").json()["demonstrativo"])
        Marco.objects.create(sala=sala, ano=1958, titulo="M", descricao="d", demonstrativo=True)
        self.assertTrue(self.get("/api/memorial/sala/6/").json()["demonstrativo"])

    def test_acao_publicar_muda_a_versao_do_totem(self):
        sala = Sala.objects.get(numero=1)
        m = Marco.objects.create(sala=sala, ano=1958, titulo="M", descricao="d")
        v = self.get("/api/memorial/versao/", sala=1).json()["versao"]
        admin_user = User.objects.create_superuser("chefe", password="senha-longa-1")
        self.client.force_login(admin_user)
        self.client.post("/admin/memorial/marco/", {
            "action": "despublicar", "_selected_action": [m.pk],
        })
        self.assertFalse(Marco.objects.get(pk=m.pk).publicado)
        self.assertNotEqual(self.get("/api/memorial/versao/", sala=1).json()["versao"], v)
        self.assertTrue(Registro.objects.filter(descricao__startswith="Tirado do totem", autor="chefe").exists())

    def test_admin_abre_com_as_abas_novas(self):
        self.client.force_login(User.objects.create_superuser("chefe", password="senha-longa-1"))
        sala = Sala.objects.get(numero=6)
        pagina = self.client.get(f"/admin/memorial/sala/{sala.pk}/change/").content.decode()
        for campo in ("apresentacao_set-0-titulo", "decada_set-TOTAL_FORMS", "marco_set-TOTAL_FORMS", "video_set-TOTAL_FORMS"):
            self.assertIn(campo, pagina)
        d = Decada.objects.create(sala=sala, rotulo="A", periodo="B", titulo="C")
        self.assertIn("acontecimentos-0-texto", self.client.get(f"/admin/memorial/decada/{d.pk}/change/").content.decode())


@override_settings(MEDIA_ROOT=MEDIA, CACHES=CACHE, REST_FRAMEWORK=limites("1000/min"))
class RegistroTests(Base):
    URL = "/administracao/"

    def setUp(self):
        super().setUp()
        Registro.objects.all().delete()
        self.chefe = User.objects.create_superuser("chefe", password="senha-longa-1")
        Registro.objects.all().delete()

    def checkin(self, **extra):
        dados = {"nome": "Maria Conceição", "ano": "1998", "turma": "3º A", "email": EMAIL, "consentimento": "true", **extra}
        return self.client.post("/api/memorial/checkin/", dados)

    def test_checkin_novo_atualizado_e_foto(self):
        self.assertEqual(self.checkin().status_code, 201)
        self.assertEqual(self.checkin(fotos=png()).status_code, 201)
        tipos = list(Registro.objects.order_by("id").values_list("tipo", "direcao", "autor"))
        self.assertEqual(tipos, [
            ("checkin_novo", "entrada", "Visitante"), ("checkin_atualizado", "entrada", "Visitante"),
            ("foto_enviada", "entrada", "Visitante"),
        ])

    def test_nunca_guarda_email(self):
        self.checkin()
        aluno_obj = Aluno.objects.get()
        aluno_obj.instagram = "fulano"
        aluno_obj.save()
        for r in Registro.objects.all():
            self.assertNotIn(EMAIL, f"{r.descricao} {r.autor} {r.busca}")

    def test_campo_isca_nao_registra(self):
        self.checkin(site="http://robo")
        self.assertEqual(Registro.objects.count(), 0)

    def test_remover_ex_aluno_apaga_o_nome_dos_registros(self):
        self.checkin(fotos=png())
        aluno_obj = Aluno.objects.get()
        pk = aluno_obj.pk
        aluno_obj.delete()
        for r in Registro.objects.all():
            self.assertNotIn("Maria", r.descricao)
            self.assertNotIn("maria", r.busca)
        self.assertTrue(Registro.objects.filter(tipo="aluno_removido", direcao="saida", aluno_ref=pk).exists())

    def test_alteracoes_da_equipe_com_autor(self):
        self.client.force_login(self.chefe)
        self.assertTrue(Registro.objects.filter(tipo="login", autor="chefe", direcao="entrada").exists())
        sala = Sala.objects.get(numero=1)
        self.client.post("/admin/memorial/marco/add/", {
            "sala": sala.pk, "ano": 1960, "titulo": "Novo", "descricao": "d", "icone": "star", "ordem": 0, "publicado": "on",
        })
        self.assertTrue(Registro.objects.filter(tipo="cadastro_criado", autor="chefe", descricao__contains="Novo").exists())
        m = Marco.objects.get()
        self.client.post(f"/admin/memorial/marco/{m.pk}/delete/", {"post": "yes"})
        self.assertTrue(Registro.objects.filter(tipo="cadastro_removido", direcao="saida", autor="chefe").exists())
        self.client.post("/admin/logout/")
        self.assertTrue(Registro.objects.filter(tipo="logout", autor="chefe", direcao="saida").exists())

    def test_login_recusado(self):
        self.client.post("/admin/login/", {"username": "chefe", "password": "errada"})
        self.assertTrue(Registro.objects.filter(tipo="login_recusado", descricao__contains="chefe").exists())
        self.assertNotIn("errada", str(list(Registro.objects.values_list("descricao", "busca"))))

    def test_login_nao_vira_alteracao_de_usuario(self):
        self.client.login(username="chefe", password="senha-longa-1")
        self.assertEqual(list(Registro.objects.values_list("tipo", flat=True)), ["login"])

    def test_acesso_ao_painel(self):
        self.assertRedirects(self.client.get(self.URL), f"/admin/login/?next={self.URL}")
        comum = User.objects.create_user("comum", password="senha-longa-1")
        self.client.force_login(comum)
        self.assertEqual(self.client.get(self.URL).status_code, 302)  # não é da equipe
        equipe = User.objects.create_user("equipe", password="senha-longa-1", is_staff=True)
        self.client.force_login(equipe)
        self.assertEqual(self.client.get(self.URL).status_code, 403)  # é da equipe, sem a permissão
        self.assertEqual(self.client.get(self.URL + "exportar.csv").status_code, 403)
        equipe.groups.add(Group.objects.get(name="Administrativo"))
        equipe = User.objects.get(pk=equipe.pk)
        self.client.force_login(equipe)
        self.assertEqual(self.client.get(self.URL).status_code, 200)

    def test_filtros_do_painel(self):
        self.checkin()
        registrar(Registro.Tipo.EXPORTACAO, "Exportação antiga", autor="ana", em=timezone.now() - timedelta(days=10))
        self.client.force_login(self.chefe)
        def nomes(**filtros):
            return [r.descricao for r in self.client.get(self.URL, filtros).context["pagina"].object_list]
        self.assertIn("Check-in: Maria Conceição (1998, 3º A)", nomes(q="conceicao maria"))
        self.assertEqual(nomes(q="ana"), ["Exportação antiga"])
        self.assertEqual(nomes(direcao="saida", q="exportacao"), ["Exportação antiga"])
        self.assertEqual(nomes(tipo="checkin_novo"), ["Check-in: Maria Conceição (1998, 3º A)"])
        dez = (timezone.localdate() - timedelta(days=10)).isoformat()
        self.assertEqual(nomes(ate=dez), ["Exportação antiga"])
        self.assertEqual(self.client.get(self.URL, {"de": "lixo", "tipo": "lixo", "direcao": "lixo", "pagina": "lixo"}).status_code, 200)

    def test_html_do_visitante_e_escapado(self):
        registrar(Registro.Tipo.CHECKIN_NOVO, "Check-in: <script>alert(1)</script>", autor="Visitante")
        self.client.force_login(self.chefe)
        pagina = self.client.get(self.URL).content.decode()
        self.assertNotIn("<script>alert", pagina)

    def test_exportar_csv_fica_registrado_e_neutraliza_formula(self):
        registrar(Registro.Tipo.CHECKIN_NOVO, "=HYPERLINK(1)", autor="Visitante")
        self.client.force_login(self.chefe)
        r = self.client.get(self.URL + "exportar.csv", {"tipo": "checkin_novo"})
        corpo = r.content.decode("utf-8-sig")
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("'=HYPERLINK(1)", corpo)
        self.assertNotIn(";=HYPERLINK", corpo)
        self.assertEqual(len(corpo.strip().splitlines()), 2)
        self.assertTrue(Registro.objects.filter(tipo="exportacao", autor="chefe", direcao="saida").exists())
        self.assertEqual(_celula("-1"), "'-1")
        self.assertEqual(_celula("Maria"), "Maria")

    def test_registro_nao_edita_nem_apaga_no_admin(self):
        registro = registrar(Registro.Tipo.LOGIN, "x", autor="y")
        self.client.force_login(self.chefe)
        base = "/admin/memorial/registro/"
        self.assertEqual(self.client.get(base).status_code, 200)
        self.assertEqual(self.client.get(base + "add/").status_code, 403)
        self.assertEqual(self.client.post(f"{base}{registro.pk}/delete/", {"post": "yes"}).status_code, 403)
        self.assertEqual(self.client.post(f"{base}{registro.pk}/change/", {"descricao": "z"}).status_code, 403)


class UtilTests(TestCase):
    def test_normalizar_e_turma(self):
        self.assertEqual(normalizar("  João  PEDRO  "), "joao pedro")
        self.assertEqual({chave_turma(t) for t in ("3º A", "3o a", "3ª A", "3 A", "3A")}, {"3a"})
        self.assertNotEqual(chave_turma("3º A"), chave_turma("3º B"))
