import streamlit as st
from db import run_query, reset_database_from_file, render_sidebar_reset

st.set_page_config(page_title="Lab Equipment Booking", page_icon="🔬", layout="wide")

# Render Sidebar Reset control
render_sidebar_reset()

st.title("🔬 Research Laboratory Equipment Booking — Dashboard")
st.caption("Centralized portal for managing lab resources, scheduling equipment, and tracking usage.")

try:
    c1, c2, c3 = st.columns(3)
    eq_count = run_query("SELECT COUNT(*) N FROM EQUIPMENT")["N"].iloc[0]
    bk_count = run_query("SELECT COUNT(*) N FROM BOOKING WHERE Status='CONFIRMED'")["N"].iloc[0]
    res_count = run_query("SELECT COUNT(*) N FROM RESEARCHER")["N"].iloc[0]

    c1.metric("Total Equipment", int(eq_count))
    c2.metric("Active Bookings", int(bk_count))
    c3.metric("Researchers", int(res_count))
except Exception as e:
    st.error(f"Database error: {e}")

st.divider()

st.subheader("System Modules")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    **Core Entities**
    - 🏢 **Department**: Academic and research departments
    - 👤 **Researcher**: Lab members, faculty, and project staff
    - 🏷️ **Equipment Category**: Categories and classifications
    """)
with col2:
    st.markdown("""
    **Equipment & Operations**
    - ⚙️ **Equipment**: Instruments, specifications, and availability
    - 🔧 **Technician**: Specialized maintenance staff
    - 📅 **Booking**: Conflict-free equipment reservations
    """)
with col3:
    st.markdown("""
    **Tracking & Reports**
    - ⏱️ **Usage Log**: Log actual equipment usage and computed hours
    - 🛠️ **Maintenance**: Service history and cost tracking
    - 🧾 **Receipt**: Generate and export booking receipts
    """)

st.divider()

st.subheader("🛠️ Database Administration")
with st.container(border=True):
    st.markdown("#### 🔄 Automatic Database Reset & Seed")
    st.write(
        "Click the button below to completely reset and re-initialize the Oracle database with the schema, "
        "sample data, constraints, triggers, and PL/SQL procedures defined in `new.txt`."
    )
    col_b1, col_b2 = st.columns([1, 2])
    with col_b1:
        if st.button("🔄 Auto-Reset Everything with new.txt", type="primary", key="btn_main_reset"):
            with st.spinner("Executing new.txt script in Oracle..."):
                success, msg, logs = reset_database_from_file("new.txt")
                if success:
                    st.success(msg)
                    if logs:
                        with st.expander("View Script Output"):
                            st.code(logs, language="text")
                    st.rerun()
                else:
                    st.error(f"Reset failed: {msg}")
    with col_b2:
        st.info("ℹ️ Drops all tables & sequences, recreates 3NF schema, reloads 10 sample records per entity, and compiles all 6 PL/SQL stored procedures & functions.")

