import asyncio
import sys

from fastmcp import Client

from servidor import mcp


async def main():
    async with Client(mcp) as cliente:
        ferramentas = await cliente.list_tools()
        print("Ferramentas disponíveis:")
        for ferramenta in ferramentas:
            print(f"  - {ferramenta.name}: {ferramenta.description}")

        tabelas = await cliente.call_tool("listar_tabelas", {})
        print("\nTabelas:", tabelas.data)

        for tabela in tabelas.data:
            total = await cliente.call_tool("contar_linhas", {"tabela": tabela})
            print(f"  {tabela}: {total.data} linhas")

        # Uso: py cliente_teste.py "sua pergunta" (sem argumento, só lista ferramentas e tabelas)
        pergunta = " ".join(sys.argv[1:])
        if pergunta:
            resultado = await cliente.call_tool("perguntar_ao_banco", {"pergunta": pergunta})
            dados = resultado.data
            print("\nSQL gerado:", dados.get("sql"))
            print("Resposta:", dados.get("resposta") or dados.get("erro"))


asyncio.run(main())
