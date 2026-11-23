import re
import time

import psycopg2


class SqlInvalido(ValueError):
    """Levantada quando o comando recebido não é um SELECT seguro."""


def validar_select(sql):
    """Aceita apenas uma instrução SELECT (ou WITH ... SELECT). Devolve o SQL limpo."""
    if not sql or not sql.strip():
        raise SqlInvalido("SQL vazio.")
    limpo = sql.strip().rstrip(";").strip()
    if ";" in limpo:
        raise SqlInvalido("Apenas uma instrução SQL é permitida.")
    if not re.match(r"(?is)^\s*(select|with)\b", limpo):
        raise SqlInvalido("Apenas comandos SELECT são permitidos.")
    return limpo


class BancoNeon:
    def __init__(self, url_conexao, timeout_ms=10000, ttl_esquema_s=300):
        self.url_conexao = url_conexao
        self.timeout_ms = timeout_ms
        self.ttl_esquema_s = ttl_esquema_s
        self._cache_esquema = None
        self._cache_em = 0.0

    def _conectar(self):
        conexao = psycopg2.connect(self.url_conexao)
        # O pooler do Neon não aceita statement_timeout como opção de conexão: usa-se SET.
        with conexao.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {int(self.timeout_ms)}")
        conexao.commit()
        conexao.set_session(readonly=True)
        return conexao

    def _executar(self, sql, parametros=None, limite=None):
        conexao = self._conectar()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(sql, parametros)
                colunas = [coluna[0] for coluna in cursor.description]
                linhas = cursor.fetchmany(limite) if limite else cursor.fetchall()
        finally:
            conexao.close()
        return [dict(zip(colunas, linha)) for linha in linhas]

    def consultar(self, sql):
        return self._executar(validar_select(sql))

    def _esquema(self):
        """Esquema {tabela: [colunas]} lido com UMA consulta e guardado em cache."""
        agora = time.monotonic()
        if self._cache_esquema and agora - self._cache_em < self.ttl_esquema_s:
            return self._cache_esquema
        linhas = self._executar(
            """
            SELECT t.table_name, c.column_name, c.data_type
            FROM information_schema.tables t
            LEFT JOIN information_schema.columns c
              ON c.table_schema = t.table_schema AND c.table_name = t.table_name
            WHERE t.table_schema = 'public'
            ORDER BY t.table_name, c.ordinal_position
            """
        )
        esquema = {}
        for linha in linhas:
            colunas = esquema.setdefault(linha["table_name"], [])
            if linha["column_name"]:
                colunas.append({"coluna": linha["column_name"], "tipo": linha["data_type"]})
        self._cache_esquema, self._cache_em = esquema, agora
        return esquema

    def listar_tabelas(self):
        return sorted(self._esquema())

    def descrever_tabela(self, tabela):
        esquema = self._esquema()
        if tabela not in esquema:
            raise ValueError(f"Tabela '{tabela}' não existe")
        return esquema[tabela]

    def esquema_completo(self):
        texto = ""
        for tabela, colunas in sorted(self._esquema().items()):
            lista = ", ".join(f"{c['coluna']} ({c['tipo']})" for c in colunas)
            texto += f"- {tabela}: {lista}\n"
        return texto


class BancoComLimite(BancoNeon):
    """Igual ao BancoNeon, mas busca no máximo `limite` linhas direto do banco."""

    def __init__(self, url_conexao, limite=10, timeout_ms=10000, ttl_esquema_s=300):
        super().__init__(url_conexao, timeout_ms, ttl_esquema_s)
        self.limite = limite

    def consultar(self, sql):
        return self._executar(validar_select(sql), limite=self.limite)
