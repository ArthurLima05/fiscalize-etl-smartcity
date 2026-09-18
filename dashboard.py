from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

CIDADES = ["recife", "olinda", "jaboatao_dos_guararapes", "paulista"]
NOMES_CIDADES = {
    "recife": "Recife",
    "olinda": "Olinda",
    "jaboatao_dos_guararapes": "Jaboatão dos Guararapes",
    "paulista": "Paulista",
}

st.set_page_config(page_title="Fiscalize Smart City — Painel Ambiental", page_icon="🌦️", layout="wide")


@st.cache_resource
def obter_engine():
    neon_url = os.getenv("NEON_DATABASE_URL")
    if not neon_url:
        st.error("Variável de ambiente NEON_DATABASE_URL não configurada no .env")
        st.stop()
    return create_engine(neon_url)


@st.cache_data(ttl=300)
def carregar_tabela(_engine, tabela: str) -> pd.DataFrame:
    try:
        return pd.read_sql(f"SELECT * FROM {tabela}", _engine)
    except SQLAlchemyError:
        return pd.DataFrame()


def aviso_tabela_vazia(cidade: str) -> None:
    st.warning(
        f"Ainda não há dados para exibir. Rode `python -m src.pipeline {cidade}` "
        "para popular o pipeline antes de usar o painel."
    )


def cor_aqi(aqi: float) -> str:
    if aqi <= 50:
        return "🟢"
    if aqi <= 100:
        return "🟡"
    return "🔴"


engine = obter_engine()
df_clima_atual = carregar_tabela(engine, "clima_atual")
df_qualidade_ar = carregar_tabela(engine, "qualidade_ar")
df_historico = carregar_tabela(engine, "historico_clima")

st.title("Fiscalize Smart City — Painel Ambiental da RMR")
st.caption(
    "Dados ambientais da Região Metropolitana do Recife usados para apoiar a priorização de "
    "chamados do Fiscalize (EMLURB, CTTU, SEMC) — chuva e temperatura para alagamentos/buracos, "
    "qualidade do ar para saúde pública."
)

cidade_selecionada = st.selectbox(
    "Cidade", CIDADES, format_func=lambda chave: NOMES_CIDADES[chave]
)

if df_clima_atual.empty and df_qualidade_ar.empty and df_historico.empty:
    aviso_tabela_vazia(cidade_selecionada)
    st.stop()

st.subheader("Condições atuais")

clima_cidade = df_clima_atual[df_clima_atual["cidade"] == cidade_selecionada] if not df_clima_atual.empty else pd.DataFrame()
ar_cidade = df_qualidade_ar[df_qualidade_ar["cidade"] == cidade_selecionada] if not df_qualidade_ar.empty else pd.DataFrame()

if clima_cidade.empty and ar_cidade.empty:
    aviso_tabela_vazia(cidade_selecionada)
else:
    ultimo_clima = clima_cidade.sort_values("coletado_em").iloc[-1] if not clima_cidade.empty else None
    ultimo_ar = ar_cidade.sort_values("coletado_em").iloc[-1] if not ar_cidade.empty else None

    colunas = st.columns(7)
    if ultimo_clima is not None:
        colunas[0].metric("Temperatura", f"{ultimo_clima['temperatura_c']:.1f} °C")
        colunas[1].metric("Umidade", f"{ultimo_clima['umidade_relativa_pct']:.0f} %")
        colunas[2].metric("Precipitação", f"{ultimo_clima['precipitacao_mm']:.1f} mm")
        colunas[3].metric("Vento", f"{ultimo_clima['vento_kmh']:.1f} km/h")
    else:
        for indice in range(4):
            colunas[indice].metric("Clima", "sem dado")

    if ultimo_ar is not None:
        colunas[4].metric("PM2.5", f"{ultimo_ar['pm2_5']:.1f} µg/m³")
        colunas[5].metric("PM10", f"{ultimo_ar['pm10']:.1f} µg/m³")
        aqi = ultimo_ar["indice_us_aqi"]
        colunas[6].metric(f"{cor_aqi(aqi)} US AQI", f"{aqi:.0f}")
    else:
        for indice in range(4, 7):
            colunas[indice].metric("Ar", "sem dado")

st.subheader("Histórico climático (últimos 7 dias)")

historico_cidade = (
    df_historico[df_historico["cidade"] == cidade_selecionada].sort_values("data")
    if not df_historico.empty
    else pd.DataFrame()
)

if historico_cidade.empty:
    aviso_tabela_vazia(cidade_selecionada)
else:
    figura_historico = go.Figure()
    figura_historico.add_trace(
        go.Bar(
            x=historico_cidade["data"],
            y=historico_cidade["precipitacao_total_mm"],
            name="Precipitação (mm)",
            marker_color="#1f77b4",
            yaxis="y2",
            opacity=0.5,
        )
    )
    figura_historico.add_trace(
        go.Scatter(
            x=historico_cidade["data"],
            y=historico_cidade["temperatura_max_c"],
            name="Temperatura máx (°C)",
            mode="lines+markers",
            line=dict(color="#d62728"),
        )
    )
    figura_historico.add_trace(
        go.Scatter(
            x=historico_cidade["data"],
            y=historico_cidade["temperatura_min_c"],
            name="Temperatura mín (°C)",
            mode="lines+markers",
            line=dict(color="#ff7f0e"),
        )
    )
    figura_historico.update_layout(
        yaxis=dict(title="Temperatura (°C)"),
        yaxis2=dict(title="Precipitação (mm)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40),
    )
    st.plotly_chart(figura_historico, use_container_width=True)

st.subheader("Comparativo entre cidades")

precipitacao_por_cidade = {}
if not df_historico.empty:
    for cidade in CIDADES:
        soma = df_historico[df_historico["cidade"] == cidade]["precipitacao_total_mm"].sum()
        precipitacao_por_cidade[cidade] = soma

aqi_por_cidade = {}
if not df_qualidade_ar.empty:
    for cidade in CIDADES:
        registros_cidade = df_qualidade_ar[df_qualidade_ar["cidade"] == cidade]
        if not registros_cidade.empty:
            aqi_por_cidade[cidade] = registros_cidade.sort_values("coletado_em").iloc[-1]["indice_us_aqi"]

if not precipitacao_por_cidade and not aqi_por_cidade:
    aviso_tabela_vazia(cidade_selecionada)
else:
    nomes = [NOMES_CIDADES[cidade] for cidade in CIDADES]
    figura_comparativo = go.Figure()
    figura_comparativo.add_trace(
        go.Bar(
            x=nomes,
            y=[precipitacao_por_cidade.get(cidade, 0) for cidade in CIDADES],
            name="Precipitação acumulada 7d (mm)",
            marker_color="#1f77b4",
        )
    )
    figura_comparativo.add_trace(
        go.Bar(
            x=nomes,
            y=[aqi_por_cidade.get(cidade, 0) for cidade in CIDADES],
            name="US AQI atual",
            marker_color="#d62728",
            yaxis="y2",
        )
    )
    figura_comparativo.update_layout(
        barmode="group",
        yaxis=dict(title="Precipitação acumulada (mm)"),
        yaxis2=dict(title="US AQI", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40),
    )
    st.plotly_chart(figura_comparativo, use_container_width=True)

st.subheader("Avaliação de risco")

precipitacao_acumulada = precipitacao_por_cidade.get(cidade_selecionada, 0)
aqi_atual = aqi_por_cidade.get(cidade_selecionada)

algum_alerta = False
if precipitacao_acumulada > 20:
    algum_alerta = True
    st.error(
        f"🌧️ Risco elevado de chamados de alagamento/buracos em {NOMES_CIDADES[cidade_selecionada]} "
        f"(precipitação acumulada de {precipitacao_acumulada:.1f} mm nos últimos 7 dias). "
        "Recomenda-se priorizar EMLURB/SEMC nesta região."
    )

if aqi_atual is not None and aqi_atual > 100:
    algum_alerta = True
    st.error(
        f"🌫️ Qualidade do ar ruim em {NOMES_CIDADES[cidade_selecionada]} (US AQI atual de {aqi_atual:.0f}). "
        "Recomenda-se atenção da saúde pública e possível ação de fiscalização ambiental."
    )

if not algum_alerta:
    st.success(f"Sem alertas de risco ambiental elevado para {NOMES_CIDADES[cidade_selecionada]} no momento.")

st.divider()

momentos_coleta = []
if not clima_cidade.empty:
    momentos_coleta.append(pd.to_datetime(clima_cidade["coletado_em"]).max())
if not ar_cidade.empty:
    momentos_coleta.append(pd.to_datetime(ar_cidade["coletado_em"]).max())

if momentos_coleta:
    ultima_coleta = max(momentos_coleta)
    st.caption(f"Última coleta: {ultima_coleta.strftime('%d/%m/%Y %H:%M:%S %Z') or ultima_coleta}")
else:
    st.caption("Última coleta: sem dados")

st.caption("Fluxo: Open-Meteo → MongoDB Atlas → Transform → NeonDB")
