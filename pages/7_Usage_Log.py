import streamlit as st
import datetime
from db import run_query, call_proc, call_func, render_sidebar_reset

render_sidebar_reset()

st.title("⏱️ Equipment Usage Logging & PL/SQL Routines")
st.caption("Demonstrating RECORD_USAGE stored procedure and GET_USAGE_HOURS stored function.")

tab_log, tab_calc = st.tabs(["📝 Record Usage (RECORD_USAGE)", "🔢 Query Hours (GET_USAGE_HOURS)"])

# READ DATA
try:
    df = run_query("""
        SELECT u.UsageID, u.BookingID, r.Name AS Researcher, e.Name AS Equipment,
               TO_CHAR(u.ActualStartTime, 'YYYY-MM-DD HH24:MI') AS ActualStart,
               TO_CHAR(u.ActualEndTime, 'YYYY-MM-DD HH24:MI') AS ActualEnd,
               ROUND(u.UsageHours, 2) AS UsageHours
        FROM USAGE_LOG u
        JOIN BOOKING b ON b.BookingID = u.BookingID
        JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
        JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
        ORDER BY u.UsageID DESC
    """)
    st.subheader("Usage Log Table")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch usage logs: {e}")
    df = None

# Available bookings for logging
try:
    bookings = run_query("""
        SELECT b.BookingID, r.Name AS Researcher, e.Name AS Equipment,
               TO_CHAR(b.BookingDate, 'YYYY-MM-DD') AS BDate, b.StartTime, b.EndTime
        FROM BOOKING b
        JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
        JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
        WHERE b.Status IN ('CONFIRMED', 'COMPLETED')
          AND b.BookingID NOT IN (SELECT BookingID FROM USAGE_LOG)
        ORDER BY b.BookingDate DESC, b.BookingID DESC
    """)
    b_map = {
        row["BOOKINGID"]: f"Booking #{row['BOOKINGID']}: {row['RESEARCHER']} ({row['EQUIPMENT']}) on {row['BDATE']}"
        for _, row in bookings.iterrows()
    } if bookings is not None and not bookings.empty else {}
except Exception:
    bookings = None
    b_map = {}

# TAB 1: RECORD USAGE PROCEDURE
with tab_log:
    st.subheader("Record Equipment Usage via RECORD_USAGE Procedure")

    if bookings is not None and not bookings.empty:
        selected_booking = st.selectbox(
            "Select Unlogged Booking",
            options=list(bookings["BOOKINGID"]),
            format_func=lambda x: b_map.get(x, f"Booking #{x}")
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            start_d = st.date_input("Actual Start Date", value=datetime.date.today(), key="start_d")
            start_t = st.time_input("Actual Start Time", value=datetime.time(9, 5), key="start_t")
        with col_s2:
            end_d = st.date_input("Actual End Date", value=datetime.date.today(), key="end_d")
            end_t = st.time_input("Actual End Time", value=datetime.time(11, 45), key="end_t")

        if st.button("Submit Usage (RECORD_USAGE)", type="primary"):
            dt_start = datetime.datetime.combine(start_d, start_t)
            dt_end = datetime.datetime.combine(end_d, end_t)
            try:
                call_proc("RECORD_USAGE", [int(selected_booking), dt_start, dt_end])
                st.success(f"Usage for Booking #{selected_booking} recorded via RECORD_USAGE procedure! Status updated to COMPLETED.")
                st.rerun()
            except Exception as e:
                st.error(f"PL/SQL Exception: {e}")
    else:
        st.info("All current bookings have already been logged, or no bookings exist.")

# TAB 2: GET_USAGE_HOURS FUNCTION
with tab_calc:
    st.subheader("Verify Usage Hours using GET_USAGE_HOURS Function")
    if df is not None and not df.empty:
        calc_usage_id = st.selectbox(
            "Select Usage Record",
            options=list(df["USAGEID"]),
            format_func=lambda x: f"UsageID #{x} (Booking #{df.set_index('USAGEID').loc[x, 'BOOKINGID']})"
        )
        if st.button("Call GET_USAGE_HOURS Function"):
            try:
                hours = call_func("GET_USAGE_HOURS", float, [int(calc_usage_id)])
                st.success(f"🎯 Function `GET_USAGE_HOURS({calc_usage_id})` returned: **{hours:.2f} hours**")
            except Exception as e:
                st.error(f"Error executing function: {e}")
    else:
        st.info("No usage records available.")
