# pages/device_status.py
import streamlit as st
from utils import api_client

def render():
    st.title("Device / System Status")
    status = api_client.get_status()
    if not status:
        st.error("No status available")
        return

    st.json(status)
    st.markdown("### Service Health")
    if status.get('status') == 'online':
        st.success(f"{status.get('service')} — Online")
    else:
        st.error(f"{status.get('service')} — Offline")
    st.write("Last processed:", status.get('last_processed'))
    st.write("Uptime seconds:", status.get('uptime_seconds'))
