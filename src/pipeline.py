from __future__ import annotations

import sys

from src.extract import OpenMeteoExtractor
from src.load import Load
from src.transform import Transform


def executar_pipeline(cidade: str) -> None:
    extract = OpenMeteoExtractor()
    transform = Transform()
    load = Load()

    print(f"[1/3] Extraindo clima atual de {cidade}...")
    clima_bruto = extract.get_clima_atual(cidade)
    load.load_mongo(colecao="clima_atual_raw", cidade=cidade, tipo="clima_atual", dado_bruto=clima_bruto)

    documentos_clima = load.buscar_mongo(colecao="clima_atual_raw", cidade=cidade, tipo="clima_atual")
    df_clima = transform.transformar_clima_atual(documentos_clima)
    linhas_gravadas = load.load_neon(df_clima, tabela="clima_atual", chave=["cidade", "coletado_em"])
    print(f"  -> {linhas_gravadas} linha(s) gravada(s) em NeonDB.clima_atual")

    print(f"[2/3] Extraindo qualidade do ar de {cidade}...")
    ar_bruto = extract.get_qualidade_ar_atual(cidade)
    load.load_mongo(colecao="qualidade_ar_raw", cidade=cidade, tipo="qualidade_ar", dado_bruto=ar_bruto)

    documentos_ar = load.buscar_mongo(colecao="qualidade_ar_raw", cidade=cidade, tipo="qualidade_ar")
    df_ar = transform.transformar_qualidade_ar(documentos_ar)
    linhas_gravadas = load.load_neon(df_ar, tabela="qualidade_ar", chave=["cidade", "coletado_em"])
    print(f"  -> {linhas_gravadas} linha(s) gravada(s) em NeonDB.qualidade_ar")

    print(f"[3/3] Extraindo histórico climático de {cidade}...")
    from datetime import datetime, timedelta

    hoje = datetime.utcnow().date()
    data_inicio = (hoje - timedelta(days=7)).isoformat()
    data_fim = (hoje - timedelta(days=1)).isoformat()

    historico_bruto = extract.get_historico_clima(cidade, data_inicio, data_fim)
    load.load_mongo(colecao="historico_clima_raw", cidade=cidade, tipo="historico_clima", dado_bruto=historico_bruto)

    documentos_historico = load.buscar_mongo(colecao="historico_clima_raw", cidade=cidade, tipo="historico_clima")
    df_historico = transform.transformar_historico_clima(documentos_historico)
    linhas_gravadas = load.load_neon(df_historico, tabela="historico_clima", chave=["cidade", "data"])
    print(f"  -> {linhas_gravadas} linha(s) gravada(s) em NeonDB.historico_clima")

    print("Pipeline concluído com sucesso.")


if __name__ == "__main__":
    cidade_escolhida = sys.argv[1] if len(sys.argv) > 1 else "recife"
    executar_pipeline(cidade_escolhida)
