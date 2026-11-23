"""Cliente MCP reutilizável: inicia o servidor (stdio) e chama suas ferramentas.

Usado pelo dashboard. O servidor roda como processo separado, com o mesmo Python
do cliente, e só ele fala com o Neon e com o LLM.

A conexão fica aberta entre as chamadas (um loop asyncio em thread própria), então o
servidor sobe uma única vez em vez de a cada pergunta.
"""

import asyncio
import os
import sys
import threading

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from pydantic_core import to_jsonable_python

CAMINHO_SERVIDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py")


class ClienteMCP:
    def __init__(self, caminho_servidor=CAMINHO_SERVIDOR):
        self.caminho_servidor = caminho_servidor
        self._cliente = None
        self._lock = asyncio.Lock()
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    async def _garantir_conexao(self):
        # O lock evita subir dois servidores se duas chamadas chegarem juntas.
        async with self._lock:
            if self._cliente is None or not self._cliente.is_connected():
                transporte = PythonStdioTransport(self.caminho_servidor, python_cmd=sys.executable)
                self._cliente = Client(transporte)
                await self._cliente.__aenter__()
            return self._cliente

    async def _chamar(self, ferramenta, argumentos):
        cliente = await self._garantir_conexao()
        resultado = await cliente.call_tool(ferramenta, argumentos)
        # Converte para list/dict/str/int simples (o fastmcp devolve tipos próprios).
        return to_jsonable_python(resultado.data)

    def chamar(self, ferramenta, **argumentos):
        """Chama uma ferramenta do servidor e devolve o resultado (síncrono)."""
        futuro = asyncio.run_coroutine_threadsafe(self._chamar(ferramenta, argumentos), self._loop)
        return futuro.result()

    def ferramentas(self):
        """Lista os nomes e descrições das ferramentas expostas pelo servidor."""

        async def listar():
            cliente = await self._garantir_conexao()
            return [(f.name, f.description) for f in await cliente.list_tools()]

        return asyncio.run_coroutine_threadsafe(listar(), self._loop).result()

    def perguntar(self, pergunta):
        """Pergunta em português. Devolve {"sql", "dados", "resposta"} ou {"erro", "sql"}."""
        return self.chamar("perguntar_ao_banco", pergunta=pergunta)
