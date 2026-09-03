from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from bench.database import Database
from bench.schema import (
    EvaluationResult,
    GroundingTask,
    Model,
    RedactionTask,
    TASK_IN_PROGRESS,
)


def make_grounding_task(
    task_id: int,
    *,
    expected_result: EvaluationResult = EvaluationResult.SUCCESS,
    twin_task_id: int | None = None,
) -> GroundingTask:
    return GroundingTask(
        id=task_id,
        checked_by="test-reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["synthetic:test"],
        source_text_extract="The deadline is 72 hours.",
        legal_query="What is the deadline?",
        expected_result=expected_result,
        twin_task_id=twin_task_id,
    )


def make_redaction_task(task_id: int) -> RedactionTask:
    return RedactionTask(
        id=task_id,
        checked_by="test-reviewer",
        status=TASK_IN_PROGRESS,
        source_text_references=["synthetic:test"],
        source_document_text="Client Alice has account CH00 0000.",
        terms_to_redact=["Alice", "CH00 0000"],
        expected_result=EvaluationResult.SUCCESS,
    )


def make_model(name: str = "test-model") -> Model:
    return Model(id=1, name=name, quantization=None)


@pytest.fixture
def database() -> Iterator[Database]:
    """Return an isolated database shared by all sessions in one test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database = Database(engine=engine)
    try:
        yield database
    finally:
        database.close()
        engine.dispose()
