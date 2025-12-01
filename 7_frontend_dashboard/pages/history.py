# pages/historical_records.py
import streamlit as st
from utils import api_client
import pandas as pd
from datetime import datetime

def render():
    st.title("Historical Records")
    start_date = st.date_input("Start date", value=datetime.utcnow().date())
    end_date = st.date_input("End date", value=datetime.utcnow().date())

    species_filter = st.multiselect("Organism type", options=api_client.CLASSES)
    contamination = st.selectbox("Contamination level", ["All","Low","Medium","High"])

    history_resp = api_client.get_history(limit=200)
    if not history_resp or 'history' not in history_resp:
        st.info("No history available.")
        return

    df = pd.DataFrame(history_resp['history'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', ascending=False)

    # simple filters (mocked)
    if species_filter:
        df = df[df['counts'].apply(lambda x: any([x.get(s,0)>0 for s in species_filter]))]

    st.dataframe(df[['timestamp','total']].head(200))

    # click to show annotated image detail
    if not df.empty:
        first = df.iloc[0]
        st.markdown("### Latest record details")
        st.write("Timestamp:", first['timestamp'])
        st.write("Counts:", first['counts'])
        st.info("Annotated image not stored in MOCK mode.")
