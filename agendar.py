"""Agenda o pipeline no Prefect: roda as 4 cidades a cada 5 minutos.

Uso (deixe o processo rodando; encerre com Ctrl+C):

    py agendar.py                 # padrão: a cada 5 minutos
    py agendar.py "*/15 * * * *"  # outro cron

Cada cidade vira um deployment próprio (assim uma falha em uma cidade não afeta as outras).
Use o Python que tem o Prefect instalado (pip install -r requirements.txt).
"""

from __future__ import annotations

import sys

from prefect import serve

from src.flow import pipeline_flow

CIDADES = ["recife", "olinda", "jaboatao_dos_guararapes", "paulista"]
CRON_PADRAO = "*/5 * * * *"


def montar_deployments(cron: str = CRON_PADRAO):
    return [
        pipeline_flow.to_deployment(
            name=f"{cidade}-cron",
            cron=cron,
            parameters={"cidade": cidade},
            tags=["fiscalize", cidade],
        )
        for cidade in CIDADES
    ]


if __name__ == "__main__":
    cron = sys.argv[1] if len(sys.argv) > 1 else CRON_PADRAO
    print(f"Agendando {len(CIDADES)} cidades com cron '{cron}'. Ctrl+C para parar.")
    serve(*montar_deployments(cron))
