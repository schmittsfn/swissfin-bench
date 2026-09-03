import streamlit as st
import pandas as pd
from bench.schema import Injection, GroundingTask
from bench.database import Database


def _render_injections_table(injections) -> None:
    st.dataframe(pd.DataFrame([{
        "ID": inj.id,
        "Injection Text": inj.injection_text[:60] + "..." if len(inj.injection_text) > 60 else inj.injection_text,
        "Tasks Using": len(inj.tasks),
    } for inj in injections]), use_container_width=True)


def _render_injection_details(database: Database, injections) -> None:
    st.subheader("Injection Details")
    inj_id = st.selectbox("Select injection:", [i.id for i in injections])
    inj = database.get_injection_by_id(inj_id)
    if not inj:
        return

    edited_text = st.text_area("Text:", inj.injection_text, height=100, key=f"injection_text_{inj.id}")
    if st.button("Update Injection", key=f"update_injection_{inj.id}"):
        try:
            database.update_injection(inj.id, {"injection_text": edited_text})
            st.success("Injection updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    st.write(f"**Tasks Using This Injection:** {len(inj.tasks)}")
    if inj.tasks:
        st.dataframe(pd.DataFrame([{
            "Task ID": t.id,
            "Type": "Grounding" if isinstance(t, GroundingTask) else "Redaction",
            "Status": t.status,
        } for t in inj.tasks]), use_container_width=True)


def _render_add_injection(database: Database) -> None:
    st.divider()
    st.subheader("Add New Injection")

    injection_text = st.text_area("Injection Text:")
    if st.button("Add Injection"):
        try:
            database.add_injection(Injection(injection_text=injection_text))
            st.success("Injection added!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def render(database: Database):
    st.title("Injections Management")

    injections = database.get_all_injections()
    if injections:
        _render_injections_table(injections)
        _render_injection_details(database, injections)
    else:
        st.info("No injections found")

    _render_add_injection(database)
