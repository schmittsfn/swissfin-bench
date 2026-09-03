import streamlit as st
import pandas as pd
from bench.schema import GroundingTask, RedactionTask, EvaluationResult
from bench.database import Database


STATUS_OPTIONS = ["task_not_started", "task_in_progress", "task_done"]


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _enum_name(value: object) -> str:
    return value.name if hasattr(value, "name") else str(value)


def _safe_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _render_all_tasks_tab(tasks: list[GroundingTask | RedactionTask]) -> None:
    if not tasks:
        st.info("No tasks found")
        return

    st.dataframe(pd.DataFrame([{
        "ID": t.id,
        "Type": "Grounding" if isinstance(t, GroundingTask) else "Redaction",
        "Status": t.status,
        "Checked By": t.checked_by,
        "Source References": "\n".join(t.source_text_references or []),
        "Injections": len(t.injections)
    } for t in tasks]), use_container_width=True)


def _render_grounding_details(database: Database, task: GroundingTask) -> None:
    col1, col2 = st.columns(2)
    col1.write(f"**ID:** {task.id}")
    col1.write(f"**Status:** {task.status}")
    col1.write(f"**Checked By:** {task.checked_by}")
    col2.write(f"**Expected Result:** {task.expected_result}")
    col2.write(f"**Twin Task:** {task.twin_task_id or 'None'}")

    st.markdown("### Edit Grounding Task")
    edit_col1, edit_col2 = st.columns(2)
    expected_options = [e.name for e in EvaluationResult]

    edit_status = edit_col1.selectbox(
        "Status",
        STATUS_OPTIONS,
        index=_safe_index(STATUS_OPTIONS, _enum_value(task.status)),
        key=f"grounding_status_{task.id}",
    )
    edit_checked_by = edit_col1.text_input(
        "Checked By",
        value=task.checked_by or "",
        key=f"grounding_checked_{task.id}",
    )
    edit_expected = edit_col2.selectbox(
        "Expected Result",
        expected_options,
        index=_safe_index(expected_options, _enum_name(task.expected_result)),
        key=f"grounding_expected_{task.id}",
    )
    edit_twin_task = edit_col2.text_input(
        "Twin Task",
        value=str(task.twin_task_id) if task.twin_task_id is not None else "",
        key=f"grounding_twin_{task.id}",
    )
    edit_legal_query = st.text_area(
        "Legal Query",
        value=task.legal_query or "",
        key=f"grounding_query_{task.id}",
    )
    edit_source_text = st.text_area(
        "Source text",
        value=task.source_text_extract or "",
        height=150,
        key=f"grounding_source_{task.id}",
    )
    edit_source_references = st.text_area(
        "Source Text References (one per line)",
        value="\n".join(task.source_text_references or []),
        key=f"grounding_references_{task.id}",
    )
    if st.button("Update Grounding Task", key=f"update_grounding_{task.id}"):
        try:
            database.update_grounding_task(
                task.id,
                {
                    "checked_by": edit_checked_by,
                    "status": edit_status,
                    "source_text_references": [reference.strip() for reference in edit_source_references.splitlines() if reference.strip()],
                    "source_text_extract": edit_source_text,
                    "legal_query": edit_legal_query,
                    "expected_result": edit_expected,
                    "twin_task_id": int(edit_twin_task) if edit_twin_task else None,
                },
            )
            st.success("Grounding task updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _render_grounding_tab(database: Database, tasks: list[GroundingTask]) -> None:
    if not tasks:
        st.info("No grounding tasks found")
        return

    st.dataframe(pd.DataFrame([{
        "ID": t.id,
        "Legal Query": t.legal_query[:50] + "..." if len(t.legal_query) > 50 else t.legal_query,
        "Expected Result": t.expected_result,
        "Status": t.status,
        "Twin Task": t.twin_task_id or "None",
        "Source References": "\n".join(t.source_text_references or []),
        "Injections": len(t.injections)
    } for t in tasks]), use_container_width=True)

    st.subheader("Grounding Task Details")
    task_id = st.selectbox("Select task:", [t.id for t in tasks])
    task = database.get_task_by_id(task_id)
    if task and isinstance(task, GroundingTask):
        _render_grounding_details(database, task)


def _render_redaction_details(database: Database, task: RedactionTask) -> None:
    col1, col2 = st.columns(2)
    col1.write(f"**ID:** {task.id}")
    col1.write(f"**Status:** {task.status}")
    col1.write(f"**Checked By:** {task.checked_by}")
    col2.write(f"**Expected Result:** {task.expected_result}")

    st.markdown("### Edit Redaction Task")
    edit_col1, edit_col2 = st.columns(2)
    expected_options = [e.name for e in EvaluationResult]

    edit_status = edit_col1.selectbox(
        "Status",
        STATUS_OPTIONS,
        index=_safe_index(STATUS_OPTIONS, _enum_value(task.status)),
        key=f"redaction_status_{task.id}",
    )
    edit_checked_by = edit_col1.text_input(
        "Checked By",
        value=task.checked_by or "",
        key=f"redaction_checked_{task.id}",
    )
    edit_expected = edit_col2.selectbox(
        "Expected Result",
        expected_options,
        index=_safe_index(expected_options, _enum_name(task.expected_result)),
        key=f"redaction_expected_{task.id}",
    )
    edit_terms = st.text_area(
        "Terms to Redact (one per line)",
        value="\n".join(task.terms_to_redact or []),
        key=f"redaction_terms_{task.id}",
    )
    edit_source_doc = st.text_area(
        "Source document",
        value=task.source_document_text or "",
        height=150,
        key=f"redaction_source_{task.id}",
    )
    edit_source_references = st.text_area(
        "Source Text References (one per line)",
        value="\n".join(task.source_text_references or []),
        key=f"redaction_references_{task.id}",
    )
    if st.button("Update Redaction Task", key=f"update_redaction_{task.id}"):
        try:
            database.update_redaction_task(
                task.id,
                {
                    "checked_by": edit_checked_by,
                    "status": edit_status,
                    "source_text_references": [reference.strip() for reference in edit_source_references.splitlines() if reference.strip()],
                    "source_document_text": edit_source_doc,
                    "terms_to_redact": [term.strip() for term in edit_terms.split("\n") if term.strip()],
                    "expected_result": edit_expected,
                },
            )
            st.success("Redaction task updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _render_redaction_tab(database: Database, tasks: list[RedactionTask]) -> None:
    if not tasks:
        st.info("No redaction tasks found")
        return

    st.dataframe(pd.DataFrame([{
        "ID": t.id,
        "Terms to Redact": str(t.terms_to_redact)[:50] + "...",
        "Expected Result": t.expected_result,
        "Status": t.status,
        "Source References": "\n".join(t.source_text_references or []),
        "Injections": len(t.injections)
    } for t in tasks]), use_container_width=True)

    st.subheader("Redaction Task Details")
    task_id = st.selectbox("Select task:", [t.id for t in tasks], key="redaction_select")
    task = database.get_task_by_id(task_id)
    if task and isinstance(task, RedactionTask):
        _render_redaction_details(database, task)


def _create_grounding_task(database: Database, col1, col2) -> None:
    legal_query = col1.text_area("Legal Query:")
    source_text = col1.text_area("Source Text Extract:")
    source_references = col1.text_area("Source Text References (one per line):")
    expected_result = col2.selectbox("Expected Result:", [e.name for e in EvaluationResult])
    checked_by = col2.text_input("Checked By:")
    if st.button("Create Grounding Task"):
        try:
            database.add_task(GroundingTask(
                legal_query=legal_query,
                source_text_extract=source_text,
                source_text_references=[reference.strip() for reference in source_references.splitlines() if reference.strip()],
                expected_result=expected_result,
                status="task_not_started",
                checked_by=checked_by,
            ))
            st.success("Grounding task created!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _create_redaction_task(database: Database, col1, col2) -> None:
    source_doc = col1.text_area("Source Document Text:")
    terms_str = col1.text_area("Terms to Redact (one per line):")
    source_references = col1.text_area("Source Text References (one per line):", key="redaction_references")
    expected_result = col2.selectbox("Expected Result:", [e.name for e in EvaluationResult], key="redaction_result")
    checked_by = col2.text_input("Checked By:", key="redaction_checked")
    if st.button("Create Redaction Task"):
        try:
            database.add_task(RedactionTask(
                source_document_text=source_doc,
                terms_to_redact=[t.strip() for t in terms_str.split("\n") if t.strip()],
                source_text_references=[reference.strip() for reference in source_references.splitlines() if reference.strip()],
                expected_result=expected_result,
                status="task_not_started",
                checked_by=checked_by,
            ))
            st.success("Redaction task created!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _render_create_task_section(database: Database) -> None:
    st.divider()
    st.subheader("Add New Task")

    col1, col2 = st.columns(2)
    task_type = col1.selectbox("Task Type:", ["Grounding", "Redaction"])
    if task_type == "Grounding":
        _create_grounding_task(database, col1, col2)
    else:
        _create_redaction_task(database, col1, col2)


def render(database: Database):
    st.title("Tasks Management")

    tab1, tab2, tab3 = st.tabs(["View All", "Grounding Tasks", "Redaction Tasks"])
    all_tasks = database.get_all_tasks()

    with tab1:
        _render_all_tasks_tab(all_tasks)

    with tab2:
        _render_grounding_tab(database, [t for t in all_tasks if isinstance(t, GroundingTask)])

    with tab3:
        _render_redaction_tab(database, [t for t in all_tasks if isinstance(t, RedactionTask)])

    _render_create_task_section(database)
