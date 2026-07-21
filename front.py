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
DB_URL        = f"{base_url}/database"
DB_UPLOAD_URL = f"{DB_URL}/upload"
DB_QUERY_URL  = f"{DB_URL}/query"

MAX_CLIENT_UPLOAD_BYTES = 200 * 1024 * 1024  # keep in sync with backend MAX_UPLOAD_BYTES


def extract_detail(response: requests.Response, fallback: str) -> str:
    """Safely pull an error 'detail' out of a response that may not be JSON."""
    try:
        return response.json().get("detail", fallback)
    except (ValueError, AttributeError):
        return f"{fallback} (HTTP {response.status_code})"


def delete_database(file_id: str):
    try:
        requests.delete(f"{DB_URL}/{file_id}", timeout=30)
    except requests.exceptions.RequestException:
        pass


def fetch_schema(file_id: str) -> str | None:
    try:
        r = requests.get(f"{DB_URL}/{file_id}/schema", timeout=30)
        if r.status_code == 200:
            return r.json().get("schema")
    except requests.exceptions.RequestException:
        pass
    return None


def reset_session():
    st.session_state.file_id = None
    st.session_state.last_uploaded_file = None
    st.session_state.upload_failed_for = None
    st.session_state.schema = None


def main():
    for key in ("file_id", "last_uploaded_file", "upload_failed_for", "schema"):
        st.session_state.setdefault(key, None)

    uploaded_file, question = render_query_upload_file()

    # File removed
    if uploaded_file is None and st.session_state.file_id:
        delete_database(st.session_state.file_id)
        reset_session()
        st.rerun()

    # New or changed file - but don't auto-retry a file that just failed to upload
    if (
        uploaded_file
        and uploaded_file.name != st.session_state.last_uploaded_file
        and uploaded_file.name != st.session_state.upload_failed_for
    ):
        if uploaded_file.size and uploaded_file.size > MAX_CLIENT_UPLOAD_BYTES:
            st.error(f"File too large (max {MAX_CLIENT_UPLOAD_BYTES // (1024*1024)}MB)")
            st.session_state.upload_failed_for = uploaded_file.name
        else:
            if st.session_state.file_id:
                delete_database(st.session_state.file_id)
                reset_session()

            with st.spinner("Uploading database..."):
                try:
                    r = requests.post(
                        DB_UPLOAD_URL,
                        files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                        timeout=120,
                    )
                    if r.status_code == 200:
                        st.session_state.file_id = r.json()["file_id"]
                        st.session_state.last_uploaded_file = uploaded_file.name
                        st.session_state.upload_failed_for = None
                        st.session_state.schema = fetch_schema(st.session_state.file_id)
                        if st.session_state.schema is None:
                            st.warning("Database uploaded, but schema could not be retrieved.")
                        st.success(f"Database '{uploaded_file.name}' ready")
                    else:
                        st.session_state.upload_failed_for = uploaded_file.name
                        st.error(extract_detail(r, "Upload failed"))
                except requests.exceptions.Timeout:
                    st.session_state.upload_failed_for = uploaded_file.name
                    st.error("Upload timed out")
                except requests.exceptions.ConnectionError:
                    st.session_state.upload_failed_for = uploaded_file.name
                    st.error("Cannot connect to server")
                except requests.exceptions.RequestException as e:
                    st.session_state.upload_failed_for = uploaded_file.name
                    st.error(f"Upload failed: {e}")

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
                    r = requests.post(
                        DB_QUERY_URL,
                        data={"file_id": st.session_state.file_id, "question": question},
                        timeout=120,
                    )
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
                    elif r.status_code == 400:
                        # The backend's ValueError handler returns 400 for both
                        # guardrail violations (blocked SQL predicates like DROP/
                        # DELETE/ATTACH/etc.) and other validation errors from
                        # generate_sql (e.g. "No tables found in schema").
                        detail = extract_detail(r, "Request rejected")
                        if "guardrail" in detail.lower() or "security" in detail.lower():
                            st.error(
                                " The generated SQL was blocked by a security guardrail "
                                "and was not executed against your database."
                            )
                            st.caption(detail)
                        else:
                            st.error(detail)
                    else:
                        st.error(extract_detail(r, "Query failed"))
                except requests.exceptions.Timeout:
                    st.error("Request timed out")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to server")
                except requests.exceptions.RequestException as e:
                    st.error(f"Query failed: {e}")


if __name__ == "__main__":
    main()

