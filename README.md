# Fiscalize Smart City ETL

Pipeline de ETL em Python (POO) que consome a API pública **[Open-Meteo](https://open-meteo.com/)**
(clima e qualidade do ar) para a Região Metropolitana do Recife, seguindo o fluxo:

```
API (Open-Meteo) -> MongoDB Atlas (bruto) -> Transform (pandas) -> NeonDB (relacional)
```

Este repositório é independente, mas complementa o projeto **Fiscalize** (app de chamados
públicos de Recife — EMLURB, CTTU, SEMC): a ideia é cruzar dados de clima/qualidade do ar
com o volume de chamados por categoria (ex.: chuva forte -> mais chamados de
alagamento/buracos) em um dashboard.

## Estrutura

- `src/extract.py` — classe `OpenMeteoExtractor`: busca dados brutos na API (clima atual,
  qualidade do ar atual, histórico climático). Valida a cidade contra o dicionário
  `CIDADES_VALIDAS`.
- `src/transform.py` — classe `Transform`: converte os documentos recuperados do MongoDB
  Atlas em `DataFrame`s limpos.
- `src/load.py` — classe `Load`: `load_mongo` (grava bruto no Atlas), `buscar_mongo`
  (recupera para a etapa de transformação) e `load_neon` (grava o DataFrame no NeonDB).
- `src/pipeline.py` — orquestra o fluxo completo ponta a ponta.

## Configuração

1. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copie `.env.example` para `.env` e preencha:
   - `MONGODB_URI`: string de conexão do cluster no MongoDB Atlas.
   - `NEON_DATABASE_URL`: string de conexão do banco no NeonDB.

## Executar

```bash
python -m src.pipeline recife
```

Cidades válidas: `recife`, `olinda`, `jaboatao_dos_guararapes`, `paulista`.

O comando acima:
1. Extrai clima atual, qualidade do ar atual e histórico climático (últimos 7 dias) da
   Open-Meteo.
2. Grava cada resposta bruta em uma coleção própria no MongoDB Atlas
   (`clima_atual_raw`, `qualidade_ar_raw`, `historico_clima_raw`).
3. Recupera os documentos do Atlas e transforma em DataFrames com pandas.
4. Grava os DataFrames em tabelas do NeonDB (`clima_atual`, `qualidade_ar`,
   `historico_clima`).

## Servidor MCP (`mcp_server/`)

Servidor [MCP](https://modelcontextprotocol.io/) (FastMCP) que expõe o NeonDB em modo
**somente leitura** para clientes como Claude Desktop/Claude Code e permite perguntas em
português (o LLM gera o SQL, o banco executa e o LLM explica).

### Arquivos

- `servidor.py` — define as ferramentas MCP.
- `banco.py` — acesso ao Neon: conexão `readonly`, `statement_timeout` de 10 s, validação
  (apenas um `SELECT`/`WITH`) e limite de 10 linhas aplicado direto no banco.
- `assistente.py` — cliente da API de LLM (lib `openai`; aceita `BASE_URL` compatível).
- `cliente_teste.py` — cliente de teste; `test_banco.py` — testes do validador de SQL.

### Ferramentas

| Ferramenta | Descrição |
|---|---|
| `listar_tabelas` | Lista as tabelas do schema `public` |
| `descrever_tabela` | Colunas e tipos de uma tabela |
| `executar_select` | Executa um único SELECT (máx. 10 linhas) |
| `contar_linhas` | Total de linhas de uma tabela |
| `perguntar_ao_banco` | Pergunta em português -> SQL -> resposta (1 nova tentativa se o SQL falhar) |

### Configuração e uso

```bash
pip install -r mcp_server/requirements.txt
```

No `.env` (veja `.env.example`): `NEON_DATABASE_URL`, `GPT` (chave da API), e opcionalmente
`MODELO` (padrão `gpt-6-luna`) e `BASE_URL`.

```bash
python mcp_server/servidor.py                                  # inicia o servidor (stdio)
python mcp_server/cliente_teste.py "Qual a cidade mais chuvosa?"   # teste ponta a ponta
python -m pytest mcp_server                                    # testes
```

### Cliente MCP no dashboard

O `dashboard.py` é o cliente real do servidor: a seção **"Servidor MCP"** usa
`mcp_server/cliente_mcp.py` (`ClienteMCP`), que inicia o `servidor.py` por stdio com o mesmo
Python do dashboard e mantém a conexão aberta entre as chamadas. Cada aba usa tools:

| Aba | Tools usadas |
|---|---|
| Perguntar (IA) | `perguntar_ao_banco` |
| Tabelas | `listar_tabelas`, `contar_linhas`, `descrever_tabela`, `executar_select` |
| SQL direto | `executar_select` |
| Tools do servidor | `list_tools` (descoberta via protocolo MCP) |

```
dashboard (pergunta) -> ClienteMCP -> servidor MCP -> LLM (gera SQL) -> NeonDB -> LLM (explica) -> dashboard
```

**Desempenho:** o servidor sobe uma única vez (em segundo plano, ao abrir a página; a primeira
vez leva dezenas de segundos por causa do import do `fastmcp`), o esquema do banco é lido com
uma consulta e fica em cache por 5 minutos. Depois do aquecimento, uma pergunta leva ~4-8 s
(quase tudo é tempo das 2 chamadas ao LLM).

```bash
streamlit run dashboard.py
```

O Python que roda o dashboard precisa ter as dependências do MCP
(`pip install -r mcp_server/requirements.txt`).

## Agendamento (Prefect serve)

`agendar.py` cria um deployment do flow por cidade (recife, olinda, jaboatao_dos_guararapes,
paulista) com cron `*/5 * * * *` (a cada 5 minutos) e o mantém rodando:

```bash
py agendar.py                  # a cada 5 minutos
py agendar.py "0 * * * *"      # outro cron (ex.: a cada hora)
```

O processo precisa ficar ligado (Ctrl+C encerra o agendamento). Use o Python que tem o
Prefect instalado. Para acompanhar as execuções: `prefect server start` em outro terminal e
abrir http://127.0.0.1:4200.
