import streamlit as st
import datetime
from db import get_connection, run_query, run_dml

st.title("📅 Equipment Booking & Conflict Detection")
st.caption("Demonstrating PL/SQL stored procedure CREATE_BOOKING with automated schedule overlap checks.")

# READ
try:
    df = run_query("""
        SELECT b.BookingID, r.Name AS Researcher, e.Name AS Equipment,
               b.BookingDate, b.StartTime, b.EndTime, b.Purpose, b.Status
        FROM BOOKING b
        JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
        JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
        ORDER BY b.BookingDate DESC, b.StartTime
    """)
    st.subheader("Existing Bookings")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch bookings: {e}")
    df = None

# Dropdowns for Researchers and Equipment
try:
    researchers = run_query("SELECT ResearcherID, Name FROM RESEARCHER WHERE Status = 'ACTIVE' ORDER BY Name")
    r_map = dict(zip(researchers["RESEARCHERID"], researchers["NAME"]))
except Exception as e:
    researchers = None
    r_map = {}

try:
    equipment = run_query("SELECT EquipmentID, Name, Status FROM EQUIPMENT WHERE Status IN ('AVAILABLE', 'BOOKED') ORDER BY Name")
    e_map = dict(zip(equipment["EQUIPMENTID"], equipment["NAME"]))
except Exception as e:
    equipment = None
    e_map = {}

# CREATE BOOKING
st.subheader("Create New Booking")
with st.form("book_form"):
    if researchers is not None and not researchers.empty:
        r_id = st.selectbox(
            "Researcher",
            options=list(researchers["RESEARCHERID"]),
            format_func=lambda x: f"{x} - {r_map.get(x, '')}"
        )
    else:
        r_id = None
        st.warning("No active researchers available.")

    if equipment is not None and not equipment.empty:
        e_id = st.selectbox(
            "Equipment",
            options=list(equipment["EQUIPMENTID"]),
            format_func=lambda x: f"{x} - {e_map.get(x, '')}"
        )
    else:
        e_id = None
        st.warning("No available equipment.")

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        b_date = st.date_input("Booking Date", value=datetime.date.today())
    with col_t2:
        start_time = st.time_input("Start Time", value=datetime.time(9, 0))
    with col_t3:
        end_time = st.time_input("End Time", value=datetime.time(11, 0))

    purpose = st.text_area("Booking Purpose / Experiment Details")

    if st.form_submit_button("Confirm Booking"):
        if r_id is None or e_id is None:
            st.warning("Please select both a researcher and equipment.")
        elif not purpose:
            st.warning("Please provide a purpose for the booking.")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.callproc("CREATE_BOOKING", [
                        int(r_id),
                        int(e_id),
                        b_date,
                        start_time.strftime("%H:%M"),
                        end_time.strftime("%H:%M"),
                        purpose
                    ])
                    conn.commit()
                    st.success("Booking created successfully!")
                    st.rerun()
                finally:
                    cur.close()
            except Exception as e:
                # Displays Oracle PL/SQL exception (e.g. ORA-20003 conflict message)
                st.error(f"Booking Error: {e}")

# CANCEL OR UPDATE STATUS
if df is not None and not df.empty:
    st.subheader("Manage Booking Status")
    selected_booking = st.selectbox(
        "Select Booking ID to manage",
        options=df["BOOKINGID"],
        format_func=lambda x: f"Booking #{x} - {df.set_index('BOOKINGID').loc[x, 'EQUIPMENT']} ({df.set_index('BOOKINGID').loc[x, 'STATUS']})"
    )
    b_row = df[df["BOOKINGID"] == selected_booking].iloc[0]
    
    st.write(f"**Current Status:** `{b_row['STATUS']}` | **Date:** {b_row['BOOKINGDATE']} | **Time:** {b_row['STARTTIME']} - {b_row['ENDTIME']}")
    
    col_c1, col_c2 = st.columns(2)
    if col_c1.button("Cancel Booking (Set Status = CANCELLED)"):
        try:
            run_dml("UPDATE BOOKING SET Status = 'CANCELLED' WHERE BookingID = :1", [int(selected_booking)])
            st.success(f"Booking #{selected_booking} marked as CANCELLED.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col_c2.button("Mark Completed (Set Status = COMPLETED)"):
        try:
            run_dml("UPDATE BOOKING SET Status = 'COMPLETED' WHERE BookingID = :1", [int(selected_booking)])
            st.success(f"Booking #{selected_booking} marked as COMPLETED.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

