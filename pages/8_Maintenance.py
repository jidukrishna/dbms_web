import streamlit as st
import datetime
from db import run_query, run_dml, render_sidebar_reset

render_sidebar_reset()

st.title("🛠️ Equipment Maintenance Management")

# READ
try:
    df = run_query("""
        SELECT m.MaintenanceID, m.EquipmentID, e.Name AS Equipment,
               m.TechnicianID, t.Name AS Technician,
               m.ScheduledDate, m.CompletedDate,
               m.MaintenanceType, m.Description, m.Cost
        FROM MAINTENANCE m
        JOIN EQUIPMENT e ON e.EquipmentID = m.EquipmentID
        JOIN TECHNICIAN t ON t.TechnicianID = m.TechnicianID
        ORDER BY m.ScheduledDate DESC
    """)
    st.subheader("Maintenance Log")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch maintenance records: {e}")
    df = None

# Dropdown data for Equipment and Technicians
try:
    equipment = run_query("SELECT EquipmentID, Name FROM EQUIPMENT ORDER BY Name")
    e_map = dict(zip(equipment["EQUIPMENTID"], equipment["NAME"]))
except Exception:
    equipment = None
    e_map = {}

try:
    technicians = run_query("SELECT TechnicianID, Name, Specialization FROM TECHNICIAN ORDER BY Name")
    t_map = {
        row["TECHNICIANID"]: f"{row['NAME']} ({row['SPECIALIZATION']})"
        for _, row in technicians.iterrows()
    } if technicians is not None and not technicians.empty else {}
except Exception:
    technicians = None
    t_map = {}

maint_types = ["Preventive", "Calibration", "Service", "Repair", "Inspection"]

# CREATE
st.subheader("Schedule Maintenance")
with st.form("add_maintenance"):
    col1, col2 = st.columns(2)
    with col1:
        if equipment is not None and not equipment.empty:
            eq_id = st.selectbox(
                "Equipment",
                options=list(equipment["EQUIPMENTID"]),
                format_func=lambda x: f"{x} - {e_map.get(x, '')}"
            )
        else:
            eq_id = None
            st.warning("No equipment available.")

        if technicians is not None and not technicians.empty:
            tech_id = st.selectbox(
                "Technician",
                options=list(technicians["TECHNICIANID"]),
                format_func=lambda x: f"{x} - {t_map.get(x, '')}"
            )
        else:
            tech_id = None
            st.warning("No technicians available.")

        sched_date = st.date_input("Scheduled Date", value=datetime.date.today())

    with col2:
        has_completed = st.checkbox("Mark as already completed?", value=False)
        comp_date = st.date_input("Completed Date", value=datetime.date.today()) if has_completed else None
        m_type = st.selectbox("Maintenance Type", maint_types)
        cost = st.number_input("Maintenance Cost (INR)", min_value=0.0, step=500.0)

    desc = st.text_area("Maintenance Description / Notes")

    if st.form_submit_button("Log Maintenance"):
        if eq_id is None or tech_id is None:
            st.warning("Please select both equipment and a technician.")
        else:
            try:
                run_dml("""
                    INSERT INTO MAINTENANCE
                    (MaintenanceID, EquipmentID, TechnicianID, ScheduledDate, CompletedDate, MaintenanceType, Description, Cost)
                    VALUES (MAINTENANCE_SEQ.NEXTVAL, :1, :2, :3, :4, :5, :6, :7)
                """, [int(eq_id), int(tech_id), sched_date, comp_date, m_type, desc, float(cost)])
                st.success("Maintenance record scheduled!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Remove Maintenance Record")
    selected_m_id = st.selectbox(
        "Select Maintenance ID",
        options=df["MAINTENANCEID"],
        format_func=lambda x: f"Record #{x}: {df.set_index('MAINTENANCEID').loc[x, 'EQUIPMENT']} - {df.set_index('MAINTENANCEID').loc[x, 'MAINTENANCETYPE']}"
    )
    row = df[df["MAINTENANCEID"] == selected_m_id].iloc[0]

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        edit_desc = st.text_area("Edit Description", row["DESCRIPTION"] or "")
        edit_cost = st.number_input("Edit Cost", value=float(row["COST"] or 0.0), min_value=0.0)
    with col_u2:
        curr_mtype_idx = maint_types.index(row["MAINTENANCETYPE"]) if row["MAINTENANCETYPE"] in maint_types else 0
        edit_mtype = st.selectbox("Edit Maintenance Type", maint_types, index=curr_mtype_idx)
        mark_done = st.checkbox("Record is completed", value=row["COMPLETEDDATE"] is not None)
        edit_cdate = st.date_input("Edit Completed Date", value=datetime.date.today()) if mark_done else None

    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("Update Record"):
        try:
            run_dml("""
                UPDATE MAINTENANCE
                SET MaintenanceType = :1, Description = :2, Cost = :3, CompletedDate = :4
                WHERE MaintenanceID = :5
            """, [edit_mtype, edit_desc, float(edit_cost), edit_cdate, int(selected_m_id)])
            st.success("Maintenance record updated!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col_btn2.button("Delete Record"):
        try:
            run_dml("DELETE FROM MAINTENANCE WHERE MaintenanceID = :1", [int(selected_m_id)])
            st.success("Maintenance record deleted!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

