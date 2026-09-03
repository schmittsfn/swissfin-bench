import streamlit as st
import pandas as pd
from bench.schema import Model
from bench.database import Database


def _render_models_table(models) -> None:
    st.dataframe(pd.DataFrame([{
        "ID": m.id,
        "Name": m.name,
        "Quantization": m.quantization or "N/A",
    } for m in models]), use_container_width=True)


def _render_model_details(database: Database, models) -> None:
    st.subheader("Model Details")
    model_id = st.selectbox("Select model:", [m.id for m in models])
    model = database.get_model_by_id(model_id)
    if not model:
        return

    edit_col1, edit_col2 = st.columns(2)
    edit_name = edit_col1.text_input("Name", value=model.name, key=f"model_name_{model.id}")
    edit_quantization = edit_col2.text_input(
        "Quantization",
        value=model.quantization or "",
        key=f"model_quantization_{model.id}",
    )
    if st.button("Update Model", key=f"update_model_{model.id}"):
        try:
            database.update_model(
                model.id,
                {
                    "name": edit_name,
                    "quantization": edit_quantization or None,
                },
            )
            st.success("Model updated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _render_add_model(database: Database) -> None:
    st.divider()
    st.subheader("Add New Model")

    col1, col2 = st.columns(2)
    name = col1.text_input("Model Name:")
    quantization = col2.text_input("Quantization (optional):")

    if st.button("Add Model"):
        try:
            database.add_model(Model(name=name, quantization=quantization or None))
            st.success("Model added!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def render(database: Database):
    st.title("Models Management")

    models = database.get_all_models()
    if models:
        _render_models_table(models)
        _render_model_details(database, models)
    else:
        st.info("No models found")

    _render_add_model(database)
