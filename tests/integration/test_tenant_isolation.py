import pytest

from sovereign_rag.container import Container
from sovereign_rag.domain.access import Principal, Role
from sovereign_rag.domain.exceptions import AuthorizationError
from sovereign_rag.domain.models import Document, Query


def _doc(doc_id: str) -> Document:
    return Document(
        id=doc_id,
        text="remote work policy allows three days per week with vpn",
        source=f"{doc_id}.md",
        region="eu-west",
    )


def test_retrieval_is_isolated_per_tenant(container: Container):
    container.ingestion.ingest([_doc("a")], tenant_id="acme")
    container.ingestion.ingest([_doc("b")], tenant_id="globex")

    acme = container.retrieval.retrieve(Query(text="remote work policy"), tenant_id="acme")
    globex = container.retrieval.retrieve(Query(text="remote work policy"), tenant_id="globex")

    assert acme and all(item.chunk.tenant_id == "acme" for item in acme)
    assert globex and all(item.chunk.tenant_id == "globex" for item in globex)


def test_unknown_tenant_returns_nothing(container: Container):
    container.ingestion.ingest([_doc("a")], tenant_id="acme")
    assert container.retrieval.retrieve(Query(text="remote work policy"), tenant_id="ghost") == []


def test_answer_scopes_to_principal_tenant(container: Container):
    container.ingestion.ingest([_doc("a")], tenant_id="acme")
    editor = Principal(subject="alice", tenant_id="acme", roles=[Role.EDITOR])
    answer = container.rag.answer(Query(text="remote work policy"), editor)
    assert answer.refused is False
    assert answer.citations


def test_answer_blocked_for_principal_without_query_permission(container: Container):
    container.ingestion.ingest([_doc("a")], tenant_id="acme")
    powerless = Principal(subject="bob", tenant_id="acme", roles=[])
    with pytest.raises(AuthorizationError):
        container.rag.answer(Query(text="remote work policy"), powerless)
