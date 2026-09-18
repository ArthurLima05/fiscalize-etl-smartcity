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
