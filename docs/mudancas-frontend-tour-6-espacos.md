# Frontend · do totem de 5 salas ao "Tour do Memorial · 6 espaços"

Branch: `feature/tour-6-espacos` · Escopo: **somente `frontend/`** (mais esta nota e um aviso no `DESIGN.md`).

## Commits

1. `feat(frontend): tour de 6 espaços …` — estrutura, telas e contrato de dados.
2. `style(frontend): identidade "Proposta B …"` — só paleta e cabeçalho. Revertível sozinho.

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

## Contrato que o backend precisa entregar (`GET /api/memorial/sala/<n>/`)

O frontend já funciona com a API antiga (cai em valores derivados), mas o conteúdo novo só aparece quando o backend mandar:

- **Salas 1 a 6** (hoje o `Sala.numero` tem validador máximo 5 e a migration 0009 cria 5). Slugs/cores:
  `fundacao #8E6918`, `diretores #2F62B0`, `professores #17805F`, `artes #C43F60`, `esporte #B85A0C`, `alunos #6E4BA8`.
  A Sala 06 deve ter `tipo: "fechamento"`; as demais, `"conteudo"`. Até isso existir, `?sala=6` dá 404.
- `apresentacao` (opcional): `{ titulo, texto: string[], foto?: url|null, legenda, icone }`.
- `decadas` (opcional, 7 itens): `{ id, rotulo: "Anos 60", periodo: "1958 a 1969", titulo, resumo, icone, foto?, acontecimentos: [{ano, texto} × 3] }`.
- `marcos[]`: 4 por espaço; campos novos opcionais `foto` (url|null) e `texto` (texto longo, aberto no toque).
- Sem `decadas`, o app monta as décadas a partir dos `marcos`; sem `apresentacao`, usa título e subtítulo da sala.
- Os tipos estão em `frontend/src/dados/tipos.ts`; o conjunto de exemplo (`dados/demo.ts` + `exemplo.json`) já segue este formato.

## Atenção

- `frontend/src/dados/exemplo.json` agora é o conteúdo do protótipo novo e **não é mais igual** ao `tour.json` do backend.
  `scripts/extrair_exemplo.py` ainda extrai o protótipo antigo e sobrescreveria o arquivo: não rode antes de atualizá-lo.
- `testes/e2e.mjs` foi atualizado para a nova estrutura, mas **não foi executado** (precisa do backend + `carregar_exemplo`
  com os 6 espaços). Os trechos que dependem do conteúdo do servidor (contagem de fotos por período) podem precisar de ajuste.
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
