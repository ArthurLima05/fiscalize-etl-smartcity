"""Camada de extração: busca dados brutos na API pública Open-Meteo."""
from __future__ import annotations

from typing import Any, Dict, Tuple

import requests


class OpenMeteoExtractor:
    """Responsável por buscar dados brutos (clima e qualidade do ar) na API Open-Meteo.

    Nenhum valor fixo específico da API (URLs base, timeout) fica espalhado pelos
    métodos: tudo é definido uma única vez no construtor.
    """

    # Dicionário de opções válidas: cidades atendidas pelo Fiscalize (Região
    # Metropolitana do Recife), cada uma com sua coordenada (latitude, longitude).
    CIDADES_VALIDAS: Dict[str, Tuple[float, float]] = {
        "recife": (-8.0578, -34.8829),
        "olinda": (-8.0089, -34.8553),
        "jaboatao_dos_guararapes": (-8.1130, -35.0150),
        "paulista": (-7.9407, -34.8730),
    }

    def __init__(self, timeout_segundos: int = 15) -> None:
        """Inicializa o extractor com os valores fixos da API Open-Meteo.

        Args:
            timeout_segundos: tempo máximo (em segundos) de espera por requisição HTTP.
        """
        self._url_forecast = "https://api.open-meteo.com/v1/forecast"
        self._url_qualidade_ar = "https://air-quality-api.open-meteo.com/v1/air-quality"
        self._url_historico = "https://archive-api.open-meteo.com/v1/archive"
        self._timeout = timeout_segundos

    def _resolver_coordenadas(self, cidade: str) -> Tuple[float, float]:
        """Valida a cidade recebida contra o dicionário `CIDADES_VALIDAS` e retorna suas coordenadas.

        Args:
            cidade: nome da cidade (chave do dicionário `CIDADES_VALIDAS`).
        """
        chave = cidade.strip().lower().replace(" ", "_")
        if chave not in self.CIDADES_VALIDAS:
            opcoes = ", ".join(self.CIDADES_VALIDAS.keys())
            raise ValueError(f"Cidade inválida: '{cidade}'. Opções válidas: {opcoes}")
        return self.CIDADES_VALIDAS[chave]

    def get_clima_atual(self, cidade: str) -> Dict[str, Any]:
        """Busca as condições climáticas atuais de uma cidade.

        Args:
            cidade: nome da cidade a consultar (deve estar em `CIDADES_VALIDAS`).
        """
        latitude, longitude = self._resolver_coordenadas(cidade)
        parametros = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "timezone": "America/Recife",
        }
        resposta = requests.get(self._url_forecast, params=parametros, timeout=self._timeout)
        resposta.raise_for_status()
        return resposta.json()

    def get_qualidade_ar_atual(self, cidade: str) -> Dict[str, Any]:
        """Busca a qualidade do ar atual (PM2.5, PM10, ozônio, índice US AQI) de uma cidade.

        Args:
            cidade: nome da cidade a consultar (deve estar em `CIDADES_VALIDAS`).
        """
        latitude, longitude = self._resolver_coordenadas(cidade)
        parametros = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,ozone,us_aqi",
            "timezone": "America/Recife",
        }
        resposta = requests.get(self._url_qualidade_ar, params=parametros, timeout=self._timeout)
        resposta.raise_for_status()
        return resposta.json()

    def get_historico_clima(self, cidade: str, data_inicio: str, data_fim: str) -> Dict[str, Any]:
        """Busca o histórico diário de clima (chuva, temperaturas máx/mín) de uma cidade.

        Args:
            cidade: nome da cidade a consultar (deve estar em `CIDADES_VALIDAS`).
            data_inicio: data inicial no formato 'YYYY-MM-DD'.
            data_fim: data final no formato 'YYYY-MM-DD'.
        """
        latitude, longitude = self._resolver_coordenadas(cidade)
        parametros = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": data_inicio,
            "end_date": data_fim,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "America/Recife",
        }
        resposta = requests.get(self._url_historico, params=parametros, timeout=self._timeout)
        resposta.raise_for_status()
        return resposta.json()
