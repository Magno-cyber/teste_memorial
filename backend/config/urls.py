from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from memorial import administracao

admin.site.site_header = "Memorial Dom Bosco"
admin.site.site_title = "Memorial Dom Bosco"
admin.site.index_title = "Salas, ex-alunos e configuração dos totens"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("administracao/", administracao.painel, name="administracao"),
    path("administracao/exportar.csv", administracao.exportar, name="administracao_exportar"),
    path("api/", include("memorial.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
