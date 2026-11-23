import pytest

from banco import SqlInvalido, validar_select


@pytest.mark.parametrize("sql", [
    "SELECT * FROM clima_atual",
    "  select 1;  ",
    "WITH t AS (SELECT 1) SELECT * FROM t",
])
def test_aceita_select(sql):
    assert validar_select(sql).lower().startswith(("select", "with"))


@pytest.mark.parametrize("sql", [
    "", "   ", "DROP TABLE clima_atual", "DELETE FROM clima_atual",
    "SELECT 1; DROP TABLE clima_atual", "UPDATE x SET a = 1",
])
def test_recusa_nao_select(sql):
    with pytest.raises(SqlInvalido):
        validar_select(sql)
