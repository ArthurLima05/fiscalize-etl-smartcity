from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


class Transform:
    def transformar_clima_atual(self, documentos: List[Dict[str, Any]]) -> pd.DataFrame:
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
