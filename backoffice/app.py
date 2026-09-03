"""Streamlit back office for browsing the Swissfin Bench result store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from backoffice._pages import dashboard, tasks, models, injections, executions, notes
from bench.database import Database

st.set_page_config(
    page_title="Swissfin Bench",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a page:", ["Dashboard", "Tasks", "Models", "Injections", "Executions", "Notes"])

with Database() as database:
    if page == "Dashboard":
        dashboard.render(database)
    elif page == "Tasks":
        tasks.render(database)
    elif page == "Models":
        models.render(database)
    elif page == "Injections":
        injections.render(database)
    elif page == "Executions":
        executions.render(database)
    elif page == "Notes":
        notes.render(database)

st.divider()
st.caption("Swissfin Bench • tasks, runs and results")
