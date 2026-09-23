"""execute_sql 가드레일. (설계 §4 "execute_sql 가드레일")

서비스 계층에서 강제한다 — SDK 훅과 달리 mock/production/테스트에서 동일하게 동작한다.
"""

import pytest

from services.sql.guard import MAX_ROWS, SqlGuardError, check_sql


ALLOWED = {"wip", "part", "route_step"}


def test_max_rows_contract_is_one_thousand() -> None:
    assert MAX_ROWS == 1000


def test_select_passes_and_gets_limit() -> None:
    guarded = check_sql("SELECT * FROM wip", ALLOWED)

    assert guarded.rstrip().endswith(f"LIMIT {MAX_ROWS + 1}")


def test_existing_limit_is_kept() -> None:
    guarded = check_sql("SELECT * FROM wip LIMIT 10", ALLOWED)

    assert guarded.count("LIMIT") == 1
    assert guarded.rstrip().endswith("LIMIT 10")


def test_with_cte_is_allowed() -> None:
    sql = "WITH x AS (SELECT * FROM part) SELECT * FROM x"
    assert check_sql(sql, ALLOWED)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM wip",
        "UPDATE wip SET pieces = 0",
        "INSERT INTO wip VALUES (1)",
        "DROP TABLE wip",
        "ALTER TABLE wip ADD COLUMN x INT",
        "CREATE TABLE t (a INT)",
        "ATTACH DATABASE 'x.db' AS x",
        "PRAGMA table_info(wip)",
    ],
)
def test_non_select_statements_are_rejected(sql: str) -> None:
    with pytest.raises(SqlGuardError):
        check_sql(sql, ALLOWED)


def test_select_containing_dml_keyword_is_rejected() -> None:
    with pytest.raises(SqlGuardError):
        check_sql("SELECT * FROM wip; DROP TABLE part", ALLOWED)


def test_multiple_statements_are_rejected() -> None:
    with pytest.raises(SqlGuardError):
        check_sql("SELECT 1 FROM part; SELECT 2 FROM part", ALLOWED)


def test_trailing_semicolon_is_fine() -> None:
    assert check_sql("SELECT * FROM part;", ALLOWED)


def test_unregistered_table_message_points_to_list_tables() -> None:
    with pytest.raises(SqlGuardError) as excinfo:
        check_sql("SELECT * FROM SECRET_TABLE", ALLOWED)

    message = str(excinfo.value)
    assert "SECRET_TABLE" in message
    assert "list_tables" in message


def test_table_match_is_case_insensitive() -> None:
    assert check_sql("select * from WIP", ALLOWED)


def test_join_tables_are_checked() -> None:
    with pytest.raises(SqlGuardError):
        check_sql(
            "SELECT * FROM part p JOIN SECRET s ON s.id = p.id", ALLOWED
        )


def test_named_parameter_from_is_not_read_as_table() -> None:
    """`BETWEEN :from AND :to` 의 `:from` 을 FROM 절로 오인하면 안 된다."""

    sql = (
        "SELECT * FROM wip WHERE due BETWEEN :from AND :to"
    )
    assert check_sql(sql, ALLOWED)


def test_subquery_from_paren_is_allowed() -> None:
    sql = "SELECT * FROM (SELECT * FROM part) t"
    assert check_sql(sql, ALLOWED)
