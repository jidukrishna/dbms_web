import streamlit as st
from db import run_query, run_dml, render_sidebar_reset

render_sidebar_reset()

st.title("🔧 Technician Management")

# READ
try:
    df = run_query("SELECT * FROM TECHNICIAN ORDER BY TechnicianID")
    st.subheader("Technician Records")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch technicians: {e}")
    df = None

# CREATE
st.subheader("Add New Technician")
with st.form("add_technician"):
    tech_id = st.number_input("Technician ID", min_value=1, step=1)
    name = st.text_input("Name")
    phone = st.text_input("Phone")
    specialization = st.text_input("Specialization (e.g. Microscopy, Electronics)")
    if st.form_submit_button("Add Technician"):
        if not name or not phone or not specialization:
            st.warning("Please fill in all fields.")
        else:
            try:
                run_dml("""
                    INSERT INTO TECHNICIAN (TechnicianID, Name, Phone, Specialization)
                    VALUES (:1, :2, :3, :4)
                """, [int(tech_id), name, phone, specialization])
                st.success("Technician added successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Delete Technician")
    selected_id = st.selectbox("Select Technician to edit/delete", df["TECHNICIANID"],
                               format_func=lambda x: f"ID {x}: {df.set_index('TECHNICIANID').loc[x, 'NAME']}")
    row = df[df["TECHNICIANID"] == selected_id].iloc[0]
    new_name = st.text_input("Edit Name", row["NAME"])
    new_phone = st.text_input("Edit Phone", row["PHONE"])
    new_spec = st.text_input("Edit Specialization", row["SPECIALIZATION"])

    col1, col2 = st.columns(2)
    if col1.button("Update Technician"):
        try:
            run_dml("""
                UPDATE TECHNICIAN
                SET Name = :1, Phone = :2, Specialization = :3
                WHERE TechnicianID = :4
            """, [new_name, new_phone, new_spec, int(selected_id)])
            st.success("Technician updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col2.button("Delete Technician"):
        try:
            run_dml("DELETE FROM TECHNICIAN WHERE TechnicianID = :1", [int(selected_id)])
            st.success("Technician deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

