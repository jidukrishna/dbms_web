import streamlit as st
import datetime
from db import run_query, run_dml, call_proc, call_func, call_proc_with_output, render_sidebar_reset

render_sidebar_reset()

st.title("📅 Equipment Booking & PL/SQL Logic")
st.caption("Demonstrates CREATE_BOOKING, CHECK_BOOKING_CONFLICT, UPDATE_BOOKING_TIME, and SHOW_RESEARCHER_BOOKINGS.")

# TABS for organized presentation
tab_list, tab_book, tab_reschedule, tab_summary = st.tabs([
    "📋 All Bookings",
    "➕ Create Booking (CREATE_BOOKING)",
    "⏰ Reschedule (UPDATE_BOOKING_TIME)",
    "🔍 Researcher Schedule (SHOW_RESEARCHER_BOOKINGS)"
])

# -------------------------------------------------------------
# TAB 1: LIST & QUICK ACTIONS
# -------------------------------------------------------------
with tab_list:
    try:
        df = run_query("""
            SELECT b.BookingID, r.Name AS Researcher, e.Name AS Equipment,
                   TO_CHAR(b.BookingDate, 'YYYY-MM-DD') AS BookingDate,
                   b.StartTime, b.EndTime, b.Purpose, b.Status
            FROM BOOKING b
            JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
            JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
            ORDER BY b.BookingDate DESC, b.StartTime
        """)
        st.subheader("Current Reservations")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to fetch bookings: {e}")
        df = None

    if df is not None and not df.empty:
        st.divider()
        st.subheader("Quick Status Actions")
        c_sel, c_act1, c_act2 = st.columns([2, 1, 1])
        with c_sel:
            selected_b_id = st.selectbox(
                "Select Booking ID to update status",
                options=df["BOOKINGID"],
                format_func=lambda x: f"Booking #{x} - {df.set_index('BOOKINGID').loc[x, 'EQUIPMENT']} [{df.set_index('BOOKINGID').loc[x, 'STATUS']}]"
            )
        with c_act1:
            st.write("")
            st.write("")
            if st.button("Cancel Booking", use_container_width=True):
                try:
                    run_dml("UPDATE BOOKING SET Status = 'CANCELLED' WHERE BookingID = :1", [int(selected_b_id)])
                    st.success(f"Booking #{selected_b_id} CANCELLED.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with c_act2:
            st.write("")
            st.write("")
            if st.button("Mark Completed", use_container_width=True):
                try:
                    run_dml("UPDATE BOOKING SET Status = 'COMPLETED' WHERE BookingID = :1", [int(selected_b_id)])
                    st.success(f"Booking #{selected_b_id} COMPLETED.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

# -------------------------------------------------------------
# Dropdown data
# -------------------------------------------------------------
try:
    researchers = run_query("SELECT ResearcherID, Name FROM RESEARCHER WHERE Status = 'ACTIVE' ORDER BY Name")
    r_map = dict(zip(researchers["RESEARCHERID"], researchers["NAME"]))
except Exception:
    researchers = None
    r_map = {}

try:
    equipment = run_query("SELECT EquipmentID, Name, Status FROM EQUIPMENT WHERE Status IN ('AVAILABLE', 'BOOKED') ORDER BY Name")
    e_map = dict(zip(equipment["EQUIPMENTID"], equipment["NAME"]))
except Exception:
    equipment = None
    e_map = {}

# -------------------------------------------------------------
# TAB 2: CREATE BOOKING (with CHECK_BOOKING_CONFLICT & CREATE_BOOKING)
# -------------------------------------------------------------
with tab_book:
    st.subheader("Schedule Equipment using CREATE_BOOKING Procedure")

    col_r, col_e = st.columns(2)
    with col_r:
        if researchers is not None and not researchers.empty:
            r_id = st.selectbox(
                "Select Researcher",
                options=list(researchers["RESEARCHERID"]),
                format_func=lambda x: f"{x} - {r_map.get(x, '')}",
                key="create_r_id"
            )
        else:
            r_id = None
            st.warning("No active researchers found.")

    with col_e:
        if equipment is not None and not equipment.empty:
            e_id = st.selectbox(
                "Select Equipment",
                options=list(equipment["EQUIPMENTID"]),
                format_func=lambda x: f"{x} - {e_map.get(x, '')}",
                key="create_e_id"
            )
        else:
            e_id = None
            st.warning("No available equipment found.")

    col_d, col_s, col_en = st.columns(3)
    with col_d:
        b_date = st.date_input("Booking Date", value=datetime.date.today(), key="create_b_date")
    with col_s:
        start_time = st.time_input("Start Time", value=datetime.time(9, 0), key="create_s_time")
    with col_en:
        end_time = st.time_input("End Time", value=datetime.time(11, 0), key="create_e_time")

    purpose = st.text_area("Booking Purpose / Experiment Details", key="create_purpose")

    col_chk, col_sub = st.columns(2)
    with col_chk:
        if st.button("🔍 Test Slot (CHECK_BOOKING_CONFLICT)"):
            if e_id is None:
                st.warning("Please select equipment.")
            else:
                try:
                    s_str = start_time.strftime("%H:%M")
                    e_str = end_time.strftime("%H:%M")
                    conflict_flag = call_func("CHECK_BOOKING_CONFLICT", int, [int(e_id), b_date, s_str, e_str])
                    if conflict_flag == 1:
                        st.error("⚠️ Conflict Detected! This slot overlaps an existing booking.")
                    else:
                        st.success("✅ Slot is Clear! No conflicts detected.")
                except Exception as e:
                    st.error(f"Error checking conflict: {e}")

    with col_sub:
        if st.button("🚀 Confirm Booking (CREATE_BOOKING)", type="primary"):
            if r_id is None or e_id is None:
                st.warning("Select both researcher and equipment.")
            elif not purpose:
                st.warning("Please specify booking purpose.")
            else:
                try:
                    s_str = start_time.strftime("%H:%M")
                    e_str = end_time.strftime("%H:%M")
                    call_proc("CREATE_BOOKING", [
                        int(r_id),
                        int(e_id),
                        b_date,
                        s_str,
                        e_str,
                        purpose
                    ])
                    st.success("🎉 Booking created successfully through CREATE_BOOKING procedure!")
                    st.rerun()
                except Exception as e:
                    st.error(f"PL/SQL Exception: {e}")

# -------------------------------------------------------------
# TAB 3: RESCHEDULE (UPDATE_BOOKING_TIME)
# -------------------------------------------------------------
with tab_reschedule:
    st.subheader("Reschedule Booking using UPDATE_BOOKING_TIME Procedure")
    if df is not None and not df.empty:
        active_bookings = df[df["STATUS"] == "CONFIRMED"]
        if not active_bookings.empty:
            resched_b_id = st.selectbox(
                "Select Confirmed Booking to Reschedule",
                options=list(active_bookings["BOOKINGID"]),
                format_func=lambda x: f"Booking #{x} - {active_bookings.set_index('BOOKINGID').loc[x, 'EQUIPMENT']} ({active_bookings.set_index('BOOKINGID').loc[x, 'BOOKINGDATE']} {active_bookings.set_index('BOOKINGID').loc[x, 'STARTTIME']}-{active_bookings.set_index('BOOKINGID').loc[x, 'ENDTIME']})"
            )
            col_rd, col_rs, col_re = st.columns(3)
            with col_rd:
                new_date = st.date_input("New Date", value=datetime.date.today(), key="resched_date")
            with col_rs:
                new_start = st.time_input("New Start Time", value=datetime.time(14, 0), key="resched_start")
            with col_re:
                new_end = st.time_input("New End Time", value=datetime.time(16, 0), key="resched_end")

            if st.button("Apply New Time (UPDATE_BOOKING_TIME)", type="primary"):
                try:
                    call_proc("UPDATE_BOOKING_TIME", [
                        int(resched_b_id),
                        new_date,
                        new_start.strftime("%H:%M"),
                        new_end.strftime("%H:%M")
                    ])
                    st.success(f"Booking #{resched_b_id} successfully rescheduled via UPDATE_BOOKING_TIME!")
                    st.rerun()
                except Exception as e:
                    st.error(f"PL/SQL Exception: {e}")
        else:
            st.info("No CONFIRMED bookings available to reschedule.")
    else:
        st.info("No bookings available.")

# -------------------------------------------------------------
# TAB 4: RESEARCHER SCHEDULE (SHOW_RESEARCHER_BOOKINGS)
# -------------------------------------------------------------
with tab_summary:
    st.subheader("Query Schedule via SHOW_RESEARCHER_BOOKINGS Procedure")
    if researchers is not None and not researchers.empty:
        summary_r_id = st.selectbox(
            "Choose Researcher",
            options=list(researchers["RESEARCHERID"]),
            format_func=lambda x: f"{x} - {r_map.get(x, '')}",
            key="summary_r_id"
        )
        if st.button("Fetch PL/SQL Schedule Output", type="primary"):
            try:
                output_lines = call_proc_with_output("SHOW_RESEARCHER_BOOKINGS", [int(summary_r_id)])
                if output_lines:
                    st.code("\n".join(output_lines), language="text")
                else:
                    st.info("No output or bookings returned for this researcher.")
            except Exception as e:
                st.error(f"Failed to execute procedure: {e}")
