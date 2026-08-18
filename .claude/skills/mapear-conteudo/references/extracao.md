# Extração — do PDF ao `evidencias.json`

Pipeline concreto. Ler PDF direto para o contexto é caro e desnecessário: `pdftotext` já está
instalado e resolve quase tudo por uma fração do custo.

---

## 1. Baixar

Cadernos e gabaritos públicos — skill `pci-concursos` (PCI é o dono do pulo
`/provas/download/`):

```bash
.venv/bin/python .claude/skills/pci-concursos/scripts/pci.py buscar \
    --cargo "Oficial de Justiça" --banca FGV --ano 2022 --max 15
.venv/bin/python .claude/skills/pci-concursos/scripts/pci.py baixar <slug> \
    --para grafos/<assunto>/fontes/
```

O `baixar` já confere PDF, grava `sha256` e roda `pdftotext -layout`. URL direta
de banca/órgão (sem o PCI) continua com `curl`:

```bash
D=grafos/<slug>/fontes
mkdir -p "$D"
curl -sSL --max-time 90 --retry 2 \
     -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" \
     -o "$D/P07.pdf" "<url>"
```

Conferir **antes** de gastar tempo com o arquivo:

```bash
file "$D/P07.pdf"                 # tem de dizer "PDF document"
pdfinfo "$D/P07.pdf" | head -5    # páginas, produtor
sha256sum "$D/P07.pdf"            # vai para evidencias.json
```

Uma página de erro HTML salva com extensão `.pdf` é o modo de falha mais comum. Se `file` não
disser PDF, registre `status: "falha"` com o motivo em `obs` e siga.

## 2. Converter

```bash
pdftotext -layout "$D/P07.pdf" "$D/P07.txt"     # preserva colunas e listas
wc -l "$D/P07.txt"
```

- `-layout` é o padrão certo para **editais** (listas numeradas mantêm a hierarquia visual).
- Para **provas em duas colunas** que saírem embaralhadas, tentar sem `-layout` (fluxo de
  leitura) ou `-raw`. Comparar as duas saídas e ficar com a legível.
- Recorte por página, quando o arquivo é grande: `pdftotext -f 12 -l 40 -layout in.pdf out.txt`.
- **Arquivo saiu vazio ou com lixo** = PDF escaneado, sem camada de texto. Não há OCR neste
  ambiente: `status: "falha"`, motivo "PDF sem camada de texto". Não adivinhar o conteúdo.

## 3. Edital → taxonomia

Localizar o anexo:

```bash
grep -n -i -E "conte[úu]do program[áa]tico|ANEXO +(II|2|III)" "$D/E01.txt" | head
sed -n '412,880p' "$D/E01.txt"        # o intervalo encontrado
```

O conteúdo programático quase sempre vem como lista numerada por disciplina:

```
DIREITO CONSTITUCIONAL: 1 Constituição: conceito, classificações... 2 Direitos e garantias
fundamentais: 2.1 Direitos e deveres individuais e coletivos. 2.2 Direitos sociais...
```

Regras de conversão:

- **Cada item numerado vira um nó.** `1` → tema, `2.1` → tópico, `2.1.1` → subtópico. A
  numeração do edital já é a hierarquia; preservá-la evita inventar estrutura.
- **Cobertura total, sem exceção.** Todo item do conteúdo programático precisa existir como nó.
  `grafo.py validar` reprova o edital que nenhum nó menciona, mas não sabe contar itens dentro
  dele — a conferência final é manual: contar os itens do anexo e os nós daquele edital.
- **Item guarda-chuva** ("noções de…", "e legislação correlata", "entre outros") entra como nó
  com `mencao: "generica"`, valendo metade.
- **Ids estáveis e legíveis**: sigla da disciplina + numeração do edital — `DC.02.01`. Nunca
  renumerar um id já publicado; um edital novo que insere um item ganha id novo (`DC.02.07`),
  não desloca os existentes.

Quando os editais divergem (o normal), **unificar rótulos**:

- mesmo conteúdo, nomes diferentes → um nó só, com os variantes em `sinonimos` e `mencao`
  apontando para os dois editais;
- um edital detalha o que o outro agrupa → manter o nível fino e marcar o edital genérico como
  `generica` no nó pai;
- item que existe em só um edital → nó normal; o próprio `E(n)` já o desconta.

## 4. Prova → questões

Identificar o bloco da disciplina no escopo e depois as questões:

```bash
grep -n -i -E "^ *(quest[ãa]o +)?[0-9]{1,3}[ .)-]" "$D/P07.txt" | head -40
grep -n -i -E "direito constitucional|conhecimentos espec" "$D/P07.txt"
```

Para cada questão do escopo, um registro:

```jsonc
{"fonte": "P07", "n": 23, "nos": ["DC.03.02"], "tipo": "jurisprudencia", "dificuldade": 3}
```

Decisões que aparecem sempre:

- **Questão que cobre dois assuntos** → listar os dois em `nos`. O script divide `1/k`; não
  escolher "o principal" arbitrariamente.
- **Classificar no nó mais específico** que a questão realmente exige. Jogar tudo no tema pai
  destrói a resolução do grafo — é o erro mais custoso desta fase.
- **Questão anulada** não conta. Se o gabarito definitivo listar anulações, excluir e anotar.
- **Questão fora do escopo** simplesmente não vira registro.
- Quando o enunciado não permitir classificar com segurança, registrar no nó pai e anotar em
  `obs`. Chutar o subtópico é pior do que perder resolução.

Preencher `n_questoes_escopo` na fonte permite conferir depois se a extração perdeu questões.

## 5. QConcursos (skill `qconcursos`)

Se `.env` tiver login, esta é a coleta primária. Sem MCP, sem sessão Chrome avulsa.

```bash
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py status
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py raiox --disciplina "Direito Constitucional" --banca FGV
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py questoes --disciplina "Direito Constitucional" --banca FGV --max 80
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py editais --orgao TRT --ano 2024
```

Registrar Raio X como **agregado**, mapeando a taxonomia deles para os ids do grafo:

```jsonc
{"id": "Q01", "tipo": "plataforma", "plataforma": "qconcursos", "banca": "FGV", "ano": 2026,
 "url": "https://www.qconcursos.com/usuario/ferramentas/raio-x/…", "acessado_em": "2026-08-17",
 "status": "ok", "obs": "Raio X FGV 2021-2026; 'Controle de constitucionalidade' → DC.03"}

{"fonte": "Q01", "nos": ["DC.03"], "peso": 47, "agregada": true}
```

Itens individuais do `qc.py questoes` entram em `questoes[]` com a URL acessada. O `ano` da
fonte agregada define o decaimento do lote; fatiar por ano quando der.

Sem `.env` ou login falho: fontes públicas + lacuna. Não contornar paywall.

## 6. Paralelização

A classificação de questões é o gargalo — é o único ponto que justifica subagentes. Um agente
por prova, **o modelo da sessão** (é extração mecânica contra uma taxonomia
fechada, não análise), cada um devolvendo o array `questoes[]` da sua prova e mais nada:

> Leia `grafos/<slug>/fontes/P07.txt`. Para cada questão de `<disciplina>`, devolva um objeto
> `{"fonte":"P07","n":<número>,"nos":[<ids>],"tipo":<tipo>,"dificuldade":1-5}`. Use apenas ids
> desta lista: `<taxonomia>`. Classifique no nó mais específico que a questão exige. Questão
> anulada ou fora do escopo: não inclua. Devolva só o array JSON.

Passar a taxonomia fechada no prompt é o que mantém os ids consistentes entre agentes. Depois,
concatenar os arrays e rodar `validar` — ids inventados aparecem ali.

Download e conversão ficam no coordenador: são baratos e sequenciais.

**Esforço por tipo de trabalho** — a mesma escala vale para todas as fases:

Use o modelo da sessão em todas as fases.

## 7. Ordem de trabalho

```
descobrir → baixar → converter → taxonomia (editais) → questões (provas) → relações → build
```

A taxonomia vem **antes** das questões, sempre: sem a lista fechada de ids, cada prova gera
rótulos próprios e o grafo vira um amontoado de sinônimos.
