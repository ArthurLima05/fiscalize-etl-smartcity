"""Camada de carga: grava o dado bruto no MongoDB Atlas (NoSQL) e o resultado
transformado no NeonDB (relacional), reaproveitando as credenciais do .env."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import create_engine

load_dotenv()


class Load:
    """Responsável por persistir dados brutos no MongoDB Atlas e dados
    transformados no NeonDB, usando as variáveis de ambiente do `.env`."""

    def __init__(self) -> None:
        """Inicializa a classe de carga lendo as credenciais do `.env`
        (`MONGODB_URI`, `MONGODB_DB_NOME` e `NEON_DATABASE_URL`)."""
        self._mongo_uri = os.getenv("MONGODB_URI")
        self._mongo_db_nome = os.getenv("MONGODB_DB_NOME", "fiscalize_smartcity")
        self._neon_url = os.getenv("NEON_DATABASE_URL")

        if not self._mongo_uri:
            raise RuntimeError("Variável de ambiente MONGODB_URI não configurada no .env")
        if not self._neon_url:
            raise RuntimeError("Variável de ambiente NEON_DATABASE_URL não configurada no .env")

        self._mongo_client = MongoClient(self._mongo_uri)

    def load_mongo(self, colecao: str, cidade: str, tipo: str, dado_bruto: Dict[str, Any]) -> str:
        """Insere o dado bruto extraído da API em uma coleção do MongoDB Atlas.

        Args:
            colecao: nome da coleção onde o documento será inserido.
            cidade: cidade à qual o dado bruto se refere.
            tipo: identifica o tipo de consulta (ex.: 'clima_atual', 'qualidade_ar').
            dado_bruto: payload bruto (JSON) retornado pela API externa.
        """
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
        """Recupera documentos brutos do MongoDB Atlas para a etapa de transformação.

        Args:
            colecao: nome da coleção a consultar.
            cidade: filtra pela cidade, se informado.
            tipo: filtra pelo tipo de consulta, se informado.
        """
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

    def load_neon(self, dataframe: pd.DataFrame, tabela: str, if_exists: str = "append") -> int:
        """Grava o DataFrame transformado em uma tabela do NeonDB (PostgreSQL).

        Args:
            dataframe: DataFrame já limpo/organizado, gerado pela classe Transform.
            tabela: nome da tabela de destino no NeonDB.
            if_exists: comportamento caso a tabela já exista ('append', 'replace' ou 'fail').
        """
        engine = create_engine(self._neon_url)
        try:
            dataframe.to_sql(tabela, engine, if_exists=if_exists, index=False)
        finally:
            engine.dispose()
        return len(dataframe)
