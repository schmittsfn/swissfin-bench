from bench.schema import (
    Comparison,
    EvaluationResult,
    Execution,
    Injection,
    Model,
    NOTE_DETERMINISTIC,
    Note,
)

from conftest import make_grounding_task, make_redaction_task
from backoffice._pages.executions import _execution_rows


def test_database_crud_covers_all_benchmark_record_types(database) -> None:
    grounding = make_grounding_task(1)
    redaction = make_redaction_task(2)
    database.add_task(grounding)
    database.add_task(redaction)

    database.update_grounding_task(
        1,
        {
            "checked_by": "second-reviewer",
            "status": "task_done",
            "source_text_references": ["updated:source"],
            "source_text_extract": "Updated grounding extract.",
            "legal_query": "Updated query?",
            "expected_result": "FAILURE",
            "twin_task_id": None,
        },
    )
    database.update_redaction_task(
        2,
        {
            "checked_by": "second-reviewer",
            "status": "task_done",
            "source_text_references": [],
            "source_document_text": "Updated private document.",
            "terms_to_redact": ["private"],
            "expected_result": "SUCCESS",
        },
    )
    assert database.get_task_by_id(1).expected_result is EvaluationResult.FAILURE
    assert database.get_task_by_id(2).terms_to_redact == ["private"]

    injection = Injection(injection_text="original")
    database.add_injection(injection)
    database.update_injection(injection.id, {"injection_text": "updated"})
    assert database.get_injection_by_id(injection.id).injection_text == "updated"

    model = Model(name="original-model", quantization=None)
    database.add_model(model)
    database.update_model(
        model.id, {"name": "updated-model", "quantization": "Q4"}
    )
    assert database.get_model_by_name("updated-model").quantization == "Q4"

    execution = Execution(
        task_id=1,
        model_id=model.id,
        timestamp="run-1",
        response='{"verdict":"No"}',
        evaluation_result=EvaluationResult.FAILURE,
        injection_evaluation_results={1: EvaluationResult.SUCCESS.value},
    )
    database.add_execution(execution)
    database.update_execution(
        execution.id,
        {"task_id": redaction.id, "model_id": model.id, "timestamp": "run-2"},
    )
    stored_execution = database.get_execution_by_id(execution.id)
    assert stored_execution.timestamp == "run-2"
    assert stored_execution.task_id == redaction.id
    assert stored_execution.model_id == model.id
    assert _execution_rows([stored_execution])[0] == {
        "Execution ID": execution.id,
        "Task ID": redaction.id,
        "Task Type": "Redaction",
        "Model": "updated-model",
        "Timestamp": "run-2",
    }

    note = Note(
        execution=execution.id,
        origin=NOTE_DETERMINISTIC,
        score="correct",
    )
    database.add_note(note)
    database.update_note(
        note.id,
        {
            "execution": execution.id,
            "origin": NOTE_DETERMINISTIC,
            "score": "verified",
        },
    )
    assert database.get_note_by_id(note.id).score == "verified"
    assert database.get_notes_by_execution(execution.id)[0].id == note.id

    comparison = Comparison(similarity=0.5)
    database.add_comparison(comparison)
    database.update_comparison(comparison.id, {"similarity": 0.75})
    assert database.get_comparison_by_id(comparison.id).similarity == 0.75

    assert len(database.get_all_tasks()) == 2
    assert len(database.get_all_models()) == 1
    assert len(database.get_all_injections()) == 1
    assert len(database.get_all_executions()) == 1
    assert len(database.get_all_notes()) == 1
