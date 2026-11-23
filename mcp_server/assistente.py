from openai import OpenAI


class AssistenteGPT:
    def __init__(self, chave_api, modelo="gpt-6-luna", base_url=None):
        self.chave_api = chave_api
        self.base_url = base_url
        self.modelo = modelo
        self._cliente = None

    @property
    def cliente(self):
        # Criado só no primeiro uso: sem a chave, as ferramentas de banco continuam funcionando.
        if self._cliente is None:
            if not self.chave_api:
                raise RuntimeError("Variável GPT (chave da API) não configurada no .env")
            self._cliente = OpenAI(api_key=self.chave_api, base_url=self.base_url)
        return self._cliente

    def perguntar(self, instrucao, pergunta):
        resposta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": instrucao},
                {"role": "user", "content": pergunta},
            ],
        )
        return resposta.choices[0].message.content.strip()

    def gerar_sql(self, pergunta, esquema, sql_anterior=None, erro=None):
        instrucao = (
            "Você é especialista em PostgreSQL. "
            "Com base nas tabelas abaixo, escreva UM comando SELECT que responda à pergunta. "
            "Responda somente com o SQL, sem explicações e sem ```.\n"
            "Inclua no SELECT, além do nome (ex.: cidade), os valores usados no cálculo "
            "(ex.: o total de chuva), para que a resposta possa citá-los.\n"
            "Os dados vêm de um pipeline e podem não incluir o dia de hoje: nunca use "
            "CURRENT_DATE/NOW() como referência. Para períodos como 'últimos N dias' ou "
            "'mais recente', use a maior data presente na própria tabela (MAX(data) ou "
            "MAX(coletado_em)).\n\n"
            f"Tabelas:\n{esquema}"
        )
        if sql_anterior and erro:
            pergunta += f"\n\nO SQL anterior falhou.\nSQL: {sql_anterior}\nErro: {erro}\nCorrija-o."
        sql = self.perguntar(instrucao, pergunta)
        return sql.replace("```sql", "").replace("```", "").strip()

    def explicar_resultado(self, pergunta, dados, sql=None):
        instrucao = (
            "Responda à pergunta do usuário em português, de forma curta, "
            "usando apenas os dados fornecidos. Os dados são o resultado do SQL informado, "
            "que já foi escrito para responder à pergunta (a ordem e os filtros do SQL "
            "fazem parte da resposta). Se os dados vierem vazios, diga que não há registros."
        )
        return self.perguntar(instrucao, f"Pergunta: {pergunta}\nSQL: {sql}\nDados: {dados}")
