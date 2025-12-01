# pages/live_monitoring.py
import streamlit as st
from utils import api_client
from PIL import Image
import io, time

def render():
    st.title("Live Monitoring")
    st.markdown("Upload a microscope image (or simulate) to run AI inference.")

    col1, col2 = st.columns([2,1])
    with col1:
        uploaded = st.file_uploader("Upload image (jpg/png)", type=['jpg','jpeg','png'])
        if uploaded:
            img_bytes = uploaded.read()
            resp = api_client.post_predict(img_bytes)
            if resp:
                st.image(resp['annotated_bytes'], caption=f"Annotated — {resp['timestamp']}", use_column_width=True)
                st.markdown("**Counts**")
                st.json(resp['counts'])
                st.metric("Total", resp['total'], delta=None)
        else:
            st.info("No image uploaded. Use 'Simulate Live' to see mock inference.")

        if st.button("Simulate Live (5 frames)"):
            for i in range(5):
                # create a blank sample image
                img = Image.new('RGB', (800,600), (240,244,250))
                buf = io.BytesIO(); img.save(buf, format='JPEG'); b = buf.getvalue()
                res = api_client.post_predict(b)
                st.image(res['annotated_bytes'], caption=res['timestamp'])
                st.write("Counts:", res['counts'])
                time.sleep(0.6)

    with col2:
        st.markdown("## Latest stats")
        stats = api_client.get_stats(hours=24)
        if stats and stats.get('timeseries'):
            latest = stats['timeseries'][-1]
            st.metric("Total (latest)", latest['total'])
            for cls in ["diatom","rotifer","copepod","algae"]:
                st.write(f"- {cls.title()}: {latest.get(cls,0)}")
        st.markdown("---")
        st.markdown("### Controls")
        st.checkbox("Auto-refresh", value=False)
        st.slider("Polling interval (sec)", 1, 10, 3)
