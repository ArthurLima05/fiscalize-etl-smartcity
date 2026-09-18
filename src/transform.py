"""Camada de transformação: converte os documentos brutos recuperados do
MongoDB Atlas em DataFrames limpos, prontos para carga no NeonDB."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


class Transform:
    """Responsável por limpar/organizar os documentos brutos (vindos do MongoDB
    Atlas) em DataFrames pandas prontos para carga no banco relacional."""

    def transformar_clima_atual(self, documentos: List[Dict[str, Any]]) -> pd.DataFrame:
        """Converte documentos brutos de clima atual em um DataFrame tabular.

        Args:
            documentos: lista de documentos lidos do MongoDB Atlas, cada um contendo
                as chaves `cidade`, `coletado_em` e `dado_bruto` (resposta da Open-Meteo).
        """
        linhas = []
        for documento in documentos:
            atual = documento["dado_bruto"]["current"]
            linhas.append(
                {
                    "cidade": documento["cidade"],
                    "coletado_em": documento["coletado_em"],
                    "temperatura_c": atual.get("temperature_2m"),
                    "umidade_relativa_pct": atual.get("relative_humidity_2m"),
                    "precipitacao_mm": atual.get("precipitation"),
                    "vento_kmh": atual.get("wind_speed_10m"),
                    "codigo_tempo": atual.get("weather_code"),
                }
            )
        return pd.DataFrame(linhas)

    def transformar_qualidade_ar(self, documentos: List[Dict[str, Any]]) -> pd.DataFrame:
        """Converte documentos brutos de qualidade do ar em um DataFrame tabular.

        Args:
            documentos: lista de documentos lidos do MongoDB Atlas, cada um contendo
                as chaves `cidade`, `coletado_em` e `dado_bruto` (resposta da Open-Meteo).
        """
        linhas = []
        for documento in documentos:
            atual = documento["dado_bruto"]["current"]
            linhas.append(
                {
                    "cidade": documento["cidade"],
                    "coletado_em": documento["coletado_em"],
                    "pm10": atual.get("pm10"),
                    "pm2_5": atual.get("pm2_5"),
                    "ozonio": atual.get("ozone"),
                    "indice_us_aqi": atual.get("us_aqi"),
                }
            )
        return pd.DataFrame(linhas)

    def transformar_historico_clima(self, documentos: List[Dict[str, Any]]) -> pd.DataFrame:
        """Converte documentos brutos de histórico diário de clima em um DataFrame tabular.

        Cada documento pode conter várias datas (série diária), então cada dia vira
        uma linha própria no DataFrame resultante.

        Args:
            documentos: lista de documentos lidos do MongoDB Atlas, cada um contendo
                as chaves `cidade`, `coletado_em` e `dado_bruto` (resposta da Open-Meteo).
        """
        linhas = []
        for documento in documentos:
            diario = documento["dado_bruto"]["daily"]
            datas = diario.get("time", [])
            for indice, data in enumerate(datas):
                linhas.append(
                    {
                        "cidade": documento["cidade"],
                        "data": data,
                        "temperatura_max_c": diario["temperature_2m_max"][indice],
                        "temperatura_min_c": diario["temperature_2m_min"][indice],
                        "precipitacao_total_mm": diario["precipitation_sum"][indice],
                    }
                )
        return pd.DataFrame(linhas)
