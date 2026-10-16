from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List

import pandas as pd
from prefect import flow, task
from prefect.logging import get_run_logger

from src.extract import OpenMeteoExtractor
from src.load import Load
from src.transform import Transform


@lru_cache(maxsize=1)
def _load() -> Load:
    return Load()


# ---------- Extract ----------


@task(name="extrair_clima_atual", retries=3, retry_delay_seconds=5)
def extrair_clima_atual(cidade: str) -> Dict[str, Any]:
    return OpenMeteoExtractor().get_clima_atual(cidade)


@task(name="extrair_qualidade_ar", retries=3, retry_delay_seconds=5)
def extrair_qualidade_ar(cidade: str) -> Dict[str, Any]:
    return OpenMeteoExtractor().get_qualidade_ar_atual(cidade)


@task(name="extrair_historico_clima", retries=3, retry_delay_seconds=5)
def extrair_historico_clima(cidade: str, dias: int) -> Dict[str, Any]:
    hoje = datetime.now(timezone.utc).date()
    data_inicio = (hoje - timedelta(days=dias)).isoformat()
    data_fim = (hoje - timedelta(days=1)).isoformat()
    return OpenMeteoExtractor().get_historico_clima(cidade, data_inicio, data_fim)


# ---------- Load (Mongo Atlas, camada bruta) ----------


@task(name="salvar_mongo", retries=2, retry_delay_seconds=5)
def salvar_mongo(colecao: str, cidade: str, tipo: str, dado_bruto: Dict[str, Any]) -> str:
    id_documento = _load().load_mongo(colecao=colecao, cidade=cidade, tipo=tipo, dado_bruto=dado_bruto)
    get_run_logger().info(f"Documento {id_documento} gravado em Mongo.{colecao}")
    return id_documento


@task(name="buscar_mongo", retries=2, retry_delay_seconds=5)
def buscar_mongo(colecao: str, cidade: str, tipo: str) -> List[Dict[str, Any]]:
    documentos = _load().buscar_mongo(colecao=colecao, cidade=cidade, tipo=tipo)
    get_run_logger().info(f"{len(documentos)} documento(s) lido(s) de Mongo.{colecao}")
    return documentos


# ---------- Transform ----------


@task(name="transformar_clima_atual")
def transformar_clima_atual(documentos: List[Dict[str, Any]]) -> pd.DataFrame:
    return Transform().transformar_clima_atual(documentos)


@task(name="transformar_qualidade_ar")
def transformar_qualidade_ar(documentos: List[Dict[str, Any]]) -> pd.DataFrame:
    return Transform().transformar_qualidade_ar(documentos)


@task(name="transformar_historico_clima")
def transformar_historico_clima(documentos: List[Dict[str, Any]]) -> pd.DataFrame:
    return Transform().transformar_historico_clima(documentos)


# ---------- Load (NeonDB, camada tratada) ----------


@task(name="carregar_neon", retries=2, retry_delay_seconds=5)
def carregar_neon(dataframe: pd.DataFrame, tabela: str, chave: List[str]) -> int:
    linhas = _load().load_neon(dataframe, tabela=tabela, chave=chave)
    get_run_logger().info(f"{linhas} linha(s) processada(s) em NeonDB.{tabela}")
    return linhas


# ---------- Flow ----------


@flow(name="pipeline-fiscalize-smartcity", log_prints=True)
def pipeline_flow(cidade: str = "recife", dias_historico: int = 7) -> Dict[str, int]:
    # Clima atual: extrair -> salvar no Mongo -> buscar -> transformar -> carregar no Neon
    clima_bruto = extrair_clima_atual(cidade)
    clima_salvo = salvar_mongo("clima_atual_raw", cidade, "clima_atual", clima_bruto)
    clima_docs = buscar_mongo("clima_atual_raw", cidade, "clima_atual", wait_for=[clima_salvo])
    clima_df = transformar_clima_atual(clima_docs)
    clima_linhas = carregar_neon(clima_df, "clima_atual", ["cidade", "coletado_em"])

    # Qualidade do ar (só começa depois que o clima atual foi carregado)
    ar_bruto = extrair_qualidade_ar(cidade, wait_for=[clima_linhas])
    ar_salvo = salvar_mongo("qualidade_ar_raw", cidade, "qualidade_ar", ar_bruto)
    ar_docs = buscar_mongo("qualidade_ar_raw", cidade, "qualidade_ar", wait_for=[ar_salvo])
    ar_df = transformar_qualidade_ar(ar_docs)
    ar_linhas = carregar_neon(ar_df, "qualidade_ar", ["cidade", "coletado_em"])

    # Histórico climático (só começa depois da qualidade do ar)
    historico_bruto = extrair_historico_clima(cidade, dias_historico, wait_for=[ar_linhas])
    historico_salvo = salvar_mongo("historico_clima_raw", cidade, "historico_clima", historico_bruto)
    historico_docs = buscar_mongo("historico_clima_raw", cidade, "historico_clima", wait_for=[historico_salvo])
    historico_df = transformar_historico_clima(historico_docs)
    historico_linhas = carregar_neon(historico_df, "historico_clima", ["cidade", "data"])

    return {
        "clima_atual": clima_linhas,
        "qualidade_ar": ar_linhas,
        "historico_clima": historico_linhas,
    }


if __name__ == "__main__":
    cidade_escolhida = sys.argv[1] if len(sys.argv) > 1 else "recife"
    pipeline_flow(cidade=cidade_escolhida)
