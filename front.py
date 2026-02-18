import pandas as pd
import streamlit as st
import requests
from src.chat_bot_ui import render_query_upload_file
from config import settings
import os

# Get the base URL from the environment variable we added to docker-compose
# Defaulting to localhost allows you to still run the code outside of Docker if needed
base_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Updated Endpoints
DB_UPLOAD_URL = f"{base_url}/database/upload"
DB_QUERY_URL  = f"{base_url}/database/query"
DB_DELETE_URL = f"{base_url}/database"
DB_SCHEMA_URL = f"{base_url}/database"



def delete_database(file_id: str):
    try:
        requests.delete(f"{DB_DELETE_URL}/{file_id}")
    except Exception:
        pass


def fetch_schema(file_id: str) -> str | None:
    try:
        r = requests.get(f"{DB_SCHEMA_URL}/{file_id}/schema", timeout=30)
        if r.status_code == 200:
            return r.json().get("schema")
    except Exception:
        pass
    return None


def reset_session():
    st.session_state.file_id = None
    st.session_state.last_uploaded_file = None
    st.session_state.schema = None


def main():
    for key in ("file_id", "last_uploaded_file", "schema"):
        st.session_state.setdefault(key, None)

    uploaded_file, question = render_query_upload_file()

    # File removed
    if uploaded_file is None and st.session_state.file_id:
        delete_database(st.session_state.file_id)
        reset_session()
        st.rerun()

    # New or changed file
    if uploaded_file and uploaded_file.name != st.session_state.last_uploaded_file:
        if st.session_state.file_id:
            delete_database(st.session_state.file_id)
            reset_session()

        with st.spinner("Uploading database..."):
            try:
                r = requests.post(DB_UPLOAD_URL, files={"file": (uploaded_file.name, uploaded_file.getvalue())}, timeout=120)
                if r.status_code == 200:
                    st.session_state.file_id = r.json()["file_id"]
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.session_state.schema = fetch_schema(st.session_state.file_id)
                    st.success(f"Database '{uploaded_file.name}' ready")
                else:
                    st.error(r.json().get("detail", "Upload failed"))
            except requests.exceptions.Timeout:
                st.error("Upload timed out")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to server")

    if st.session_state.schema:
        with st.expander("Database Schema", expanded=False):
            st.code(st.session_state.schema, language="sql")

    if st.button("Ask", width="stretch"):
        if not st.session_state.file_id:
            st.warning("Please upload a database file first")
        elif not question.strip():
            st.warning("Please enter a question")
        else:
            with st.spinner("Processing..."):
                try:
                    r = requests.post(DB_QUERY_URL, data={"file_id": st.session_state.file_id, "question": question}, timeout=120)
                    if r.status_code == 200:
                        result = r.json()
                        st.divider()
                        if result.get("sql"):
                            st.code(result["sql"], language="sql")
                        if isinstance(result.get("answer"), list) and result["answer"]:
                            st.dataframe(pd.DataFrame(result["answer"]), width="stretch")
                        else:
                            st.info("No results found")
                    elif r.status_code == 404:
                        st.error("Database not found. Please re-upload your file.")
                        reset_session()
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Query failed"))
                except requests.exceptions.Timeout:
                    st.error("Request timed out")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to server")


if __name__ == "__main__":
    main()

    