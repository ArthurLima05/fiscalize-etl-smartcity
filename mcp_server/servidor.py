import os
import sys

# Permite rodar de qualquer pasta (ex.: caminho absoluto configurado em um cliente MCP).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastmcp import FastMCP

from assistente import AssistenteGPT
from banco import BancoComLimite, SqlInvalido

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv()

banco = BancoComLimite(os.getenv("NEON_DATABASE_URL"))
gpt = AssistenteGPT(
    os.getenv("GPT"),
    os.getenv("MODELO") or "gpt-6-luna",
    os.getenv("BASE_URL") or None,
)

mcp = FastMCP("Servidor Neon + GPT - Fiscalize SmartCity")


@mcp.tool
def listar_tabelas() -> list[str]:
    """Lista as tabelas disponíveis no banco NeonDB (schema public)."""
    return banco.listar_tabelas()


@mcp.tool
def descrever_tabela(tabela: str) -> list[dict]:
    """Retorna as colunas e os tipos de uma tabela do banco."""
    return banco.descrever_tabela(tabela)


@mcp.tool
def executar_select(sql: str) -> list[dict]:
    """Executa um único comando SELECT (somente leitura) e devolve as linhas (máximo 10)."""
    return banco.consultar(sql)


@mcp.tool
def contar_linhas(tabela: str) -> int:
    """Conta quantas linhas uma tabela possui."""
    if tabela not in banco.listar_tabelas():
        raise ValueError(f"Tabela '{tabela}' não existe")
    return banco.consultar(f'SELECT COUNT(*) AS total FROM "{tabela}"')[0]["total"]


@mcp.tool
def perguntar_ao_banco(pergunta: str) -> dict:
    """Responde uma pergunta em português: o GPT gera o SQL, o banco executa e o GPT explica.

    Se o SQL gerado falhar, tenta mais uma vez informando o erro ao modelo.
    Em caso de falha, devolve {"erro": ..., "sql": ...} em vez de uma exceção.
    """
    sql = None
    try:
        esquema = banco.esquema_completo()
        sql = gpt.gerar_sql(pergunta, esquema)
        try:
            dados = banco.consultar(sql)
        except Exception as erro:
            sql = gpt.gerar_sql(pergunta, esquema, sql_anterior=sql, erro=str(erro))
            dados = banco.consultar(sql)
        resposta = gpt.explicar_resultado(pergunta, dados, sql)
    except SqlInvalido as erro:
        return {"erro": f"SQL recusado: {erro}", "sql": sql}
    except Exception as erro:
        return {"erro": f"Falha ao responder a pergunta: {erro}", "sql": sql}
    return {"sql": sql, "dados": dados, "resposta": resposta}


if __name__ == "__main__":
    mcp.run()
