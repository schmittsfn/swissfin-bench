import streamlit as st
import pandas as pd
from datetime import datetime
from bench.schema import Execution, GroundingTask
from bench.database import Database


def _execution_rows(executions) -> list[dict]:
    rows = []
    for exe in sorted(executions, key=lambda x: x.timestamp, reverse=True):
        task = exe.task
        model = exe.model
        rows.append({
            "Execution ID": exe.id,
            "Task ID": exe.task_id,
            "Task Type": "Grounding" if isinstance(task, GroundingTask) else "Redaction",
            "Model": model.name if model else "Unknown",
            "Timestamp": exe.timestamp,
        })
    return rows


def _render_executions_table(database: Database, executions) -> None:
    st.dataframe(pd.DataFrame(_execution_rows(executions)), use_container_width=True)


def _render_execution_details(database: Database, exe: Execution) -> None:
    task = exe.task
    model = exe.model
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Execution ID:** {exe.id}")
    col1.write(f"**Task ID:** {task.id}")
    col2.write(f"**Model:** {model.name if model else 'Unknown'}")
    col2.write(f"**Timestamp:** {exe.timestamp}")
    col3.write(f"**Task Type:** {'Grounding' if isinstance(task, GroundingTask) else 'Redaction'}")

    st.markdown("### Edit Execution")
    edit_col1, edit_col2 = st.columns(2)
    task_ids = [t.id for t in database.get_all_tasks()]
    model_ids = [m.id for m in database.get_all_models()]
    edit_task = edit_col1.selectbox(
        "Task",
        task_ids,
        index=(task_ids.index(exe.task_id) if exe.task_id in task_ids else 0),
        key=f"execution_task_{exe.id}",
    )
    edit_model = edit_col2.selectbox(
        "Model",
        model_ids,
        index=(model_ids.index(exe.model_id) if exe.model_id in model_ids else 0),
        key=f"execution_model_{exe.id}",
    )
    edit_timestamp = st.text_input(
        "Timestamp",
        value=exe.timestamp or "",
        key=f"execution_timestamp_{exe.id}",
    )
    if st.button("Update Execution", key=f"update_execution_{exe.id}"):
        try:
            database.update_execution(
                exe.id,
                {
                    "task_id": edit_task,
                    "model_id": edit_model,
                    "timestamp": edit_timestamp,
                },
            )
            st.success("Execution updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if exe.response:
        st.text_area("Response:", exe.response, disabled=True, height=150)
    else:
        st.info("No response recorded yet")

    notes = database.get_notes_by_execution(exe.id)
    if notes:
        st.subheader("Associated Notes")
        st.dataframe(pd.DataFrame([{
            "Note ID": n.id,
            "Origin": n.origin,
            "Score": n.score,
        } for n in notes]), use_container_width=True)


def _render_add_execution(database: Database) -> None:
    st.divider()
    st.subheader("Add New Execution")

    tasks = database.get_all_tasks()
    models = database.get_all_models()

    if not tasks or not models:
        st.warning("Need at least one task and one model to create an execution")
        return

    col1, col2 = st.columns(2)
    task_id = col1.selectbox("Task:", [t.id for t in tasks])
    model_id = col2.selectbox("Model:", [m.id for m in models])
    if st.button("Create Execution"):
        try:
            database.add_execution(Execution(task_id=task_id, model_id=model_id, timestamp=datetime.now().isoformat()))
            st.success("Execution created!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def render(database: Database):
    st.title("Executions Management")

    executions = database.get_all_executions()
    if executions:
        _render_executions_table(database, executions)

        st.subheader("Execution Details")
        exec_id = st.selectbox("Select execution:", [e.id for e in executions])
        exe = database.get_execution_by_id(exec_id)
        if exe:
            _render_execution_details(database, exe)
    else:
        st.info("No executions found")

    _render_add_execution(database)
