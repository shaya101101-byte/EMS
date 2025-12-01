# pages/sensor_dashboard.py
import streamlit as st
from utils import api_client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import random

def render():
    st.title("Sensor Dashboard (Simulated)")
    st.info("Sensor values are simulated in AI-only mode.")

    # Generate simulated series
    now = datetime.utcnow()
    times = [now - timedelta(minutes=15*i) for i in range(48)][::-1]
    df = pd.DataFrame({
        'timestamp': times,
        'temperature': [random.uniform(20,30) for _ in times],
        'pH': [random.uniform(6.8,8.4) for _ in times],
        'turbidity': [random.uniform(0,10) for _ in times],
        'do': [random.uniform(5,9) for _ in times],
    }).set_index('timestamp')

    st.line_chart(df[['temperature','pH','turbidity','do']])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Temperature (°C)", f"{df['temperature'].iloc[-1]:.1f}")
    col2.metric("pH", f"{df['pH'].iloc[-1]:.2f}")
    col3.metric("Turbidity (NTU)", f"{df['turbidity'].iloc[-1]:.2f}")
    col4.metric("Dissolved O2 (mg/L)", f"{df['do'].iloc[-1]:.2f}")

    st.markdown("### Sensor thresholds")
    st.write("- Temperature normal: 18–30 °C")
    st.write("- pH normal: 6.5–8.5")
    st.write("- Turbidity normal: 0–5 NTU")
    st.write("- DO normal: >5 mg/L")
