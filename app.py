import os

import requests
import streamlit as st


def api_base_url() -> str:
    explicit = os.environ.get("API_URL")
    if explicit:
        return explicit.rstrip("/")
    hostport = os.environ.get("API_HOSTPORT")
    if hostport:
        return f"http://{hostport}"
    return "http://127.0.0.1:8000"


API_URL = api_base_url()

st.set_page_config(page_title="Football Club", page_icon="⚽")
st.title("⚽ Football Club")
st.write("A simple Hello World using FastAPI and Streamlit.")

if st.button("Say hello"):
    try:
        response = requests.get(f"{API_URL}/", timeout=30)
        response.raise_for_status()
        st.success(response.json().get("message", "Hello World"))
    except requests.RequestException as exc:
        st.error(
            "Could not reach the FastAPI server. "
            "Locally: `uvicorn api:app --reload`. On Render: wait for the API service to come up."
        )
        st.caption(str(exc))
else:
    st.info("Click the button to fetch Hello World from FastAPI.")
