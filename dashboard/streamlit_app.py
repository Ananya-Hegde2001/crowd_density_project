import streamlit as st
import json
import time
import os
import uuid

# Configure the page
st.set_page_config(page_title="🚦 Crowd Density Estimator", layout="wide")

st.title("🧠 Real-Time Crowd Density Dashboard")

# Zone-level color codes
LEVEL_COLORS = {
    "Low": "#d4edda",       # Green
    "Medium": "#fff3cd",    # Yellow
    "High": "#f8d7da",      # Orange
    "Critical": "#f5c6cb"   # Red
}

# Load zone data from detection output
def load_data():
    try:
        with open("./backend/zone_data.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"⚠️ Error loading zone data: {e}")
        return None

# Load alert logs
def load_logs():
    log_path = "./alerts/logs.txt"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return f.readlines()
    return []

# Auto-refresh every second using Streamlit rerun hack
while True:
    data = load_data()
    
    if data:
        total = data.get("total", 0)
        zones = data.get("zones", [])

        st.markdown(f"### 👥 Total People Detected: **{total}**")

        num_cols = 3  # 3x3 zone grid
        for i in range(0, len(zones), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(zones):
                    zone = zones[idx]
                    color = LEVEL_COLORS.get(zone["level"], "#eeeeee")
                    with col:
                        st.markdown(
                            f"""
                            <div style="background-color:{color}; padding: 1rem; border-radius: 12px; border:1px solid #ccc; text-align:center;">
                                <h5>Zone {zone['id']}</h5>
                                <p><strong>Count:</strong> {zone['count']}</p>
                                <p><strong>Level:</strong> {zone['level']}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        # 🚨 Critical Alerts
        critical_zones = [z for z in zones if z["level"] == "Critical"]
        if critical_zones:
            st.error(f"🚨 {len(critical_zones)} Critical Zone(s) Detected!")
    else:
        st.warning("❌ Waiting for detection data...")

    # 📜 Show Alert Logs
    st.markdown("---")
    st.markdown("### 📜 Alert Logs")
    logs = load_logs()
    if logs:
        st.text_area("Recent Alerts (Last 10)", value="".join(logs[-10:]), height=200, key=f"alerts_log_{uuid.uuid4()}")
    else:
        st.info("✅ No recent alerts.")

    time.sleep(1)
    st.rerun()
