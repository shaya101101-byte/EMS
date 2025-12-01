# pages/organism_statistics.py
import streamlit as st
from utils import api_client
import pandas as pd
import plotly.express as px

def render():
    st.title("Organism Statistics")
    hours = st.slider("Hours to plot", min_value=6, max_value=168, value=48, step=6)
    species = st.selectbox("Species", ["All"] + api_client.CLASSES)

    stats = api_client.get_stats(hours=hours)
    if not stats or 'timeseries' not in stats:
        st.info("No stats available.")
        return

    df = pd.DataFrame(stats['timeseries'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').last(f"{hours}H")

    if species == "All":
        fig = px.line(df, x=df.index, y=["total"] + api_client.CLASSES, labels={'value':'count', 'timestamp':'time'})
    else:
        fig = px.line(df, x=df.index, y=species, labels={'value':'count', 'timestamp':'time'})
    st.plotly_chart(fig, use_container_width=True)

    # pie chart latest distribution
    latest = df.iloc[-1]
    pie = pd.DataFrame({'species': api_client.CLASSES, 'count':[latest.get(c,0) for c in api_client.CLASSES]})
    fig2 = px.pie(pie, values='count', names='species', title='Latest distribution')
    st.plotly_chart(fig2, use_container_width=True)

    # summary table
    summary = df[["total"] + api_client.CLASSES].agg(['min','max','mean']).T
    summary.columns = ['min','max','avg']
    st.dataframe(summary)
