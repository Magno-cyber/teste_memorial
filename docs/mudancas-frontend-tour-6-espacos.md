# Frontend · do totem de 5 salas ao "Tour do Memorial · 6 espaços"

Escopo: **somente `frontend/`**, mais a documentação (`README.md`, `PRODUCT.md`, `DESIGN.md` e esta nota).

## Commits

1. `feat(frontend): tour de 6 espaços …` — estrutura, telas e contrato de dados.
2. `style(frontend): identidade "Proposta B …"` — só paleta e cabeçalho. Revertível sozinho.
3. `docs: nota de mudanças …` — este arquivo (primeira versão).
4. `style(frontend): cartão do perfil na cor do espaço` — pedido do Henry: o cartão (ano, turma, redes) deixou de ser
   dourado e passou a usar a cor da Sala 06 (roxo `#6E4BA8`, em degradê), com texto branco.
5. `fix(frontend): abas da Sala 06 não respondiam depois de abrir Colegas` — o título da busca ficava por cima da
   barra de abas e capturava o toque; a barra ganhou `z-index: 5` (`totem.css`).
6. `docs: README, PRODUCT e DESIGN` — atualização da documentação para os 6 espaços.

## Arquivos principais

| Arquivo | O que é |
|---|---|
| `frontend/src/dados/salas.ts` | as 6 salas (slug, nome, subtítulo, cor, tipo) e o helper `dois(n)` |
| `frontend/src/dados/tipos.ts` | contrato da API (`Apresentacao`, `Decada`, `Acontecimento`, campos novos de `Marco`) |
| `frontend/src/dados/regras.ts` | `decadasDaSala`, `apresentacaoDaSala`, `nomeDaDecada`, `marcosOrdenados` (com testes) |
| `frontend/src/dados/demo.ts` + `exemplo.json` | conteúdo de demonstração do tour novo |
| `frontend/src/telas/SalaConteudo.tsx` | tela única dos 6 espaços (abas, overlays e a aba Colegas) |
| `frontend/src/telas/Apresentacao.tsx`, `LinhaDoTempo.tsx`, `Marcos.tsx` | as telas novas |
| `frontend/src/telas/Colegas.tsx`, `Busca.tsx`, `Perfil.tsx` | aba Colegas (antes `SalaFechamento`), busca e perfil em formato de rede social |
| `frontend/src/telas/AbasSala.tsx`, `estado.ts` | abas em pílula e estado do totem (`linha`, `marcoAberto`, `perfilAba`) |
| `frontend/src/componentes/FotoEpoca.tsx` | foto com tom sépia e moldura |
| `frontend/src/estilos/tokens.css`, `contraste.test.ts` | paleta Proposta B e teste de contraste (inclui Sala 06) |

Removidos: `telas/Historia.tsx` e `telas/SalaFechamento.tsx`. Novo ícone `home` em `componentes/Icone.tsx`.

## O que mudou na tela

| Antes | Agora |
|---|---|
| 5 salas (Educação, Troféus, Artes, Professoras, Fechamento) | 6 espaços: Fundação, Diretores, Professores, Artes, Esporte, Alunos |
| Abas História, Fotos, Vídeos | Apresentação, Linha do tempo, Marcos, Fotos, Vídeos (+ **Colegas** na Sala 06) |
| Linha do tempo horizontal com marcos | Linha do tempo = 7 décadas (1958–1969 … 2020–2026) com painel (foto, resumo, 3 acontecimentos) |
| — | Marcos = 4 cartões por espaço; o toque abre o texto explicativo |
| Sala 5 só com a busca de ex-alunos | Sala 06 = as 5 abas + Colegas (busca e perfil em formato de rede social) |
| Rótulos "SALA 5", "Sala 5 de 5" | "SALA 06", "Sala 06 de 06" |

Mantidos: Fotos e Vídeos (inclusive overlays), inatividade (90 s + 15 s) voltando à Apresentação, Voltar do Android,
teclado virtual, cache offline, modo demo (`VITE_MODO_DEMO=1`), alvos de toque ≥ 56 px.

Fora do escopo, de propósito (não existem na API): botão "Conectar", "Abrir no celular" (QR do perfil), cidade, LinkedIn,
categorias de álbum. O perfil mostra só o que a API já entrega (ano, turma, Instagram/Facebook, fotos aprovadas, colegas).

## Contrato do backend (`GET /api/memorial/sala/<n>/`)

Implementado no backend (migrações `0010` a `0012`) e cadastrado pelo `/admin`:

- **Salas 1 a 6**. Slugs/cores:
  `fundacao #8E6918`, `diretores #2F62B0`, `professores #17805F`, `artes #C43F60`, `esporte #B85A0C`, `alunos #6E4BA8`.
  A Sala 06 tem `tipo: "fechamento"`; as demais, `"conteudo"`.
- `apresentacao` (opcional): `{ titulo, texto: string[], foto?: url|null, legenda, icone }`.
- `decadas` (opcional, 7 itens): `{ id, rotulo: "Anos 60", periodo: "1958 a 1969", titulo, resumo, icone, foto?, acontecimentos: [{ano, texto} × 3] }`.
- `marcos[]`: 4 por espaço; campos novos opcionais `foto` (url|null) e `texto` (texto longo, aberto no toque).
- Sem `decadas`, o app monta as décadas a partir dos `marcos`; sem `apresentacao`, usa título e subtítulo da sala.
- Os tipos estão em `frontend/src/dados/tipos.ts`; o conjunto de exemplo (`dados/demo.ts` + `exemplo.json`) já segue este formato.

## Atenção

- `frontend/src/dados/exemplo.json` e o `tour.json` do backend têm o mesmo conteúdo: mude os dois juntos.
  `scripts/extrair_exemplo.py` ainda extrai o protótipo antigo e sobrescreveria os dois: não rode antes de atualizá-lo.
- Contraste: o protótipo tinha dois pares abaixo de 4,5:1 (dourado-texto sobre champanhe, 4,37; cinza secundário sobre branco
  gelo, 4,19) e a cor Esporte não sustenta texto em branco gelo (4,37). Escurecemos os dois tons e o texto sobre a cor do espaço
  é branco puro. O `contraste.test.ts` cobre isso.
- `DESIGN.md` ganhou um aviso: suas tabelas ainda descrevem a paleta anterior.

## Como conferir

```bash
cd frontend
npm ci && npm run typecheck && npm run test:unit && npm run build
VITE_MODO_DEMO=1 npm run dev     # abra /?sala=1 … /?sala=6 em 1600×900
```
