# app.py
import streamlit as st
from importlib import import_module
import os

# 🔥 ADD THIS
import utils.api_client as api

st.set_page_config(page_title="Microscopy AI Dashboard", layout="wide")

# Load CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("assets/styles.css")

# Load logo if it exists
if os.path.exists("assets/logo.png"):
    st.sidebar.image("assets/logo.png", use_column_width=False, width=120)

st.sidebar.title("Microscopy AI Dashboard")

PAGES = {
    "Live Monitoring": "pages.live_monitoring",
    "Organism Statistics": "pages.organism_statistics",
    "Historical Records": "pages.historical_records",
    "Sensor Dashboard": "pages.sensor_dashboard",
    "Alerts": "pages.alerts",
    "Device Status": "pages.device_status",
}

page_name = st.sidebar.radio("Navigation", list(PAGES.keys()))
st.sidebar.markdown("---")

mode = st.sidebar.selectbox("Mode", ["MOCK (no backend)", "CONNECT to backend"])

# ⭐ IMPORTANT: CONNECT STREAMLIT ↔ BACKEND
if mode == "CONNECT to backend":
    api_url = st.sidebar.text_input("Backend base URL", value="http://127.0.0.1:8000")
    api.set_mode(mock=False, api_base=api_url)
    st.success("Connected to backend!")
else:
    api.set_mode(mock=True)
    st.warning("Running in MOCK mode (fake AI results).")

st.sidebar.markdown("Built for: Embedded Intelligent Microscopy System — AI-only")
st.sidebar.markdown(" ")

# Dynamically import and render page
module_name = PAGES[page_name]
module = import_module(module_name)
if hasattr(module, "render"):
    module.render()
else:
    st.error("Page module missing render() function.")
