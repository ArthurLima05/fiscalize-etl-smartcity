from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

load_dotenv()


class Load:
    def __init__(self) -> None:
        self._mongo_uri = os.getenv("MONGODB_URI")
        self._mongo_db_nome = os.getenv("MONGODB_DB_NOME", "fiscalize_smartcity")
        self._neon_url = os.getenv("NEON_DATABASE_URL")

        if not self._mongo_uri:
            raise RuntimeError("Variável de ambiente MONGODB_URI não configurada no .env")
        if not self._neon_url:
            raise RuntimeError("Variável de ambiente NEON_DATABASE_URL não configurada no .env")

        self._mongo_client = MongoClient(self._mongo_uri)

    def load_mongo(self, colecao: str, cidade: str, tipo: str, dado_bruto: Dict[str, Any]) -> str:
        banco = self._mongo_client[self._mongo_db_nome]
        documento = {
            "cidade": cidade,
            "tipo": tipo,
            "coletado_em": datetime.now(timezone.utc).isoformat(),
            "dado_bruto": dado_bruto,
        }
        resultado = banco[colecao].insert_one(documento)
        return str(resultado.inserted_id)

    def buscar_mongo(
        self, colecao: str, cidade: Optional[str] = None, tipo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        banco = self._mongo_client[self._mongo_db_nome]
        filtro: Dict[str, Any] = {}
        if cidade:
            filtro["cidade"] = cidade
        if tipo:
            filtro["tipo"] = tipo

        documentos = list(banco[colecao].find(filtro))
        for documento in documentos:
            documento["_id"] = str(documento["_id"])
        return documentos

    def load_neon(self, dataframe: pd.DataFrame, tabela: str, chave: List[str]) -> int:
        """Grava no Neon com chave primária composta; linhas já existentes são ignoradas."""
        dataframe = dataframe.drop_duplicates(subset=chave)
        engine = create_engine(self._neon_url)
        try:
            self._garantir_tabela(engine, dataframe, tabela, chave)
            with engine.begin() as conexao:
                dataframe.to_sql(
                    tabela,
                    conexao,
                    if_exists="append",
                    index=False,
                    method=self._insert_ignorando_conflito,
                )
        finally:
            engine.dispose()
        return len(dataframe)

    @staticmethod
    def _garantir_tabela(engine, dataframe: pd.DataFrame, tabela: str, chave: List[str]) -> None:
        if inspect(engine).has_table(tabela):
            return
        dataframe.head(0).to_sql(tabela, engine, index=False)
        colunas = ", ".join(f'"{coluna}"' for coluna in chave)
        with engine.begin() as conexao:
            conexao.execute(text(f'ALTER TABLE "{tabela}" ADD PRIMARY KEY ({colunas})'))

    @staticmethod
    def _insert_ignorando_conflito(tabela, conexao, colunas, linhas) -> None:
        registros = [dict(zip(colunas, linha)) for linha in linhas]
        comando = pg_insert(tabela.table).values(registros).on_conflict_do_nothing()
        conexao.execute(comando)
