# pages/alerts.py
import streamlit as st
from utils import api_client

def render():
    st.title("Alerts")
    alerts_resp = api_client.get_alerts()
    alerts = alerts_resp.get('alerts', []) if alerts_resp else []

    if not alerts:
        st.success("No alerts")
        return

    for a in alerts:
        level = a.get('level','info')
        ts = a.get('timestamp', '')
        msg = a.get('message', a.get('msg', 'Alert'))
        if level == 'red':
            st.error(f"{ts} — {msg}")
        elif level == 'yellow':
            st.warning(f"{ts} — {msg}")
        else:
            st.info(f"{ts} — {msg}")

    if st.button("Clear alerts (mock)"):
        st.success("Alerts cleared (mock)")
