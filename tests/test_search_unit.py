import pytest
from nxflow.search import SearchError, compile_clause, compile_query, tokenize
from sqlalchemy.dialects import postgresql

DIALECT = postgresql.dialect()


def _sql(clause) -> str:
    return str(clause.compile(dialect=DIALECT))


def test_tokenize_handles_quotes():
    assert tokenize('status:active tag:"prod web"') == ["status:active", "tag:prod web"]


def test_tokenize_rejects_unbalanced_quotes():
    with pytest.raises(SearchError):
        tokenize('tag:"unterminated')


def test_status_and_type():
    assert "resources.status" in _sql(compile_clause("status:active"))
    assert "resources.type" in _sql(compile_clause("type:server"))


def test_tag_uses_array_containment():
    assert "@>" in _sql(compile_clause("tag:prod"))


def test_attribute_lookup_parses_types():
    sql = _sql(compile_clause("attr.power:450"))
    assert "resources.attributes @>" in sql


def test_metadata_lookup():
    assert "resources.metadata @>" in _sql(compile_clause("meta.asset_id:A-1042"))


def test_location_prefix():
    assert "LIKE" in _sql(compile_clause("location:dc1/row3"))


def test_free_text_matches_name():
    assert "resources.name ILIKE" in _sql(compile_clause("web-01"))


def test_unknown_key_rejected():
    with pytest.raises(SearchError):
        compile_clause("bogus:value")


def test_compile_query_ands_all_tokens():
    clauses = compile_query("status:active tag:prod")
    assert len(clauses) == 2


def test_compile_query_empty():
    assert compile_query(None) == []
    assert compile_query("   ") == []
