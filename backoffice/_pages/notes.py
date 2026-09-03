import streamlit as st
import pandas as pd
from bench.schema import Note, Execution
from bench.database import Database


ORIGIN_OPTIONS = ["note_deterministic", "note_judge"]


def _origin_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _render_notes_table(notes) -> None:
    st.dataframe(pd.DataFrame([{
        "Note ID": n.id,
        "Execution ID": n.execution,
        "Origin": n.origin,
        "Score": n.score,
    } for n in notes]), use_container_width=True)


def _render_note_details(database: Database, notes, executions) -> None:
    st.subheader("Note Details")
    note_id = st.selectbox("Select note:", [n.id for n in notes])
    note = database.get_note_by_id(note_id)
    if not note:
        return

    execution_ids = [e.id for e in executions]
    edit_col1, edit_col2 = st.columns(2)
    edit_execution = edit_col1.selectbox(
        "Execution",
        execution_ids,
        index=(execution_ids.index(note.execution) if note.execution in execution_ids else 0),
        key=f"note_execution_{note.id}",
    )

    current_origin = _origin_value(note.origin)
    edit_origin = edit_col1.selectbox(
        "Origin",
        ORIGIN_OPTIONS,
        index=(ORIGIN_OPTIONS.index(current_origin) if current_origin in ORIGIN_OPTIONS else 0),
        key=f"note_origin_{note.id}",
    )

    edit_score = edit_col2.text_input("Score", value=note.score or "", key=f"note_score_{note.id}")
    if st.button("Update Note", key=f"update_note_{note.id}"):
        try:
            database.update_note(
                note.id,
                {
                    "execution": edit_execution,
                    "origin": edit_origin,
                    "score": edit_score,
                },
            )
            st.success("Note updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _render_add_note(database: Database, executions) -> None:
    st.divider()
    st.subheader("Add New Note")

    if not executions:
        st.warning("No executions available. Create an execution first.")
        return

    col1, col2 = st.columns(2)
    exec_id = col1.selectbox("Execution:", [e.id for e in executions])
    origin = col1.selectbox("Origin:", ORIGIN_OPTIONS)
    score = col2.text_input("Score:")
    if st.button("Add Note"):
        try:
            database.add_note(Note(execution=exec_id, origin=origin, score=score))
            st.success("Note added!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def render(database: Database):
    st.title("Notes Management")

    notes = database.get_all_notes()
    executions = database.get_all_executions()
    if notes:
        _render_notes_table(notes)
        _render_note_details(database, notes, executions)
    else:
        st.info("No notes found")

    _render_add_note(database, executions)
