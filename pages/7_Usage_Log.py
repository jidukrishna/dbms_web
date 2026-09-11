import streamlit as st
import datetime
from db import run_query, run_dml

st.title("⏱️ Equipment Usage Logging")
st.caption("Track actual equipment usage time. Notice that UsageHours is a derived/virtual column calculated by Oracle.")

# READ
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
    st.subheader("Usage Records")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch usage logs: {e}")
    df = None

# Available bookings for logging (filter bookings that are not cancelled)
try:
    bookings = run_query("""
        SELECT b.BookingID, r.Name AS Researcher, e.Name AS Equipment,
               TO_CHAR(b.BookingDate, 'YYYY-MM-DD') AS BDate, b.StartTime, b.EndTime
        FROM BOOKING b
        JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
        JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
        WHERE b.Status <> 'CANCELLED'
        ORDER BY b.BookingDate DESC, b.BookingID DESC
    """)
    b_map = {
        row["BOOKINGID"]: f"Booking #{row['BOOKINGID']}: {row['RESEARCHER']} ({row['EQUIPMENT']}) on {row['BDATE']}"
        for _, row in bookings.iterrows()
    } if bookings is not None and not bookings.empty else {}
except Exception as e:
    bookings = None
    b_map = {}

# CREATE LOG
st.subheader("Record Equipment Usage")
default_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
default_end = (datetime.datetime.now() + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")

with st.form("log_usage"):
    if bookings is not None and not bookings.empty:
        booking_id = st.selectbox(
            "Select Booking",
            options=list(bookings["BOOKINGID"]),
            format_func=lambda x: b_map.get(x, f"Booking #{x}")
        )
    else:
        booking_id = None
        st.warning("No active bookings found.")

    start_dt = st.text_input("Actual Start (YYYY-MM-DD HH:MM)", value=default_start)
    end_dt = st.text_input("Actual End (YYYY-MM-DD HH:MM, optional)", value=default_end)

    if st.form_submit_button("Record Usage"):
        if booking_id is None:
            st.warning("Please select a valid booking.")
        elif not start_dt:
            st.warning("Actual Start time is required.")
        else:
            try:
                # If end_dt is provided, insert with end time; else insert with NULL
                if end_dt.strip():
                    run_dml("""
                        INSERT INTO USAGE_LOG (UsageID, BookingID, ActualStartTime, ActualEndTime)
                        VALUES (USAGE_SEQ.NEXTVAL, :1,
                                TO_DATE(:2, 'YYYY-MM-DD HH24:MI'),
                                TO_DATE(:3, 'YYYY-MM-DD HH24:MI'))
                    """, [int(booking_id), start_dt.strip(), end_dt.strip()])
                else:
                    run_dml("""
                        INSERT INTO USAGE_LOG (UsageID, BookingID, ActualStartTime, ActualEndTime)
                        VALUES (USAGE_SEQ.NEXTVAL, :1,
                                TO_DATE(:2, 'YYYY-MM-DD HH24:MI'), NULL)
                    """, [int(booking_id), start_dt.strip()])

                # Optionally update booking status to COMPLETED
                run_dml("UPDATE BOOKING SET Status = 'COMPLETED' WHERE BookingID = :1", [int(booking_id)])

                st.success("Usage recorded successfully! UsageHours automatically computed.")
                st.rerun()
            except Exception as e:
                st.error(f"Error recording usage: {e}")

