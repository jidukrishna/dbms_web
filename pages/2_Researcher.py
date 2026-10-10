import streamlit as st
from db import run_query, run_dml, render_sidebar_reset

render_sidebar_reset()

st.title("👤 Researcher Management")

# READ
try:
    df = run_query("""
        SELECT r.ResearcherID, r.Name, r.Email, r.Phone, r.Role, r.Status,
               r.DeptID, d.DepartmentName
        FROM RESEARCHER r
        JOIN DEPARTMENT d ON d.DeptID = r.DeptID
        ORDER BY r.ResearcherID
    """)
    st.subheader("Researcher Directory")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch researchers: {e}")
    df = None

# Departments for FK dropdown
try:
    depts = run_query("SELECT DeptID, DepartmentName FROM DEPARTMENT ORDER BY DeptID")
    dept_map = dict(zip(depts["DEPTID"], depts["DEPARTMENTNAME"]))
except Exception as e:
    depts = None
    dept_map = {}

# CREATE
st.subheader("Add New Researcher")
with st.form("add_researcher"):
    r_id = st.number_input("Researcher ID", min_value=1, step=1)
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    role = st.text_input("Role (e.g., Research Scientist, Fellow)")
    status = st.selectbox("Status", ["ACTIVE", "INACTIVE"])
    
    if depts is not None and not depts.empty:
        dept_id = st.selectbox(
            "Department",
            options=depts["DEPTID"],
            format_func=lambda x: f"{x} - {dept_map.get(x, '')}"
        )
    else:
        dept_id = None
        st.warning("No departments available. Please create a department first.")

    if st.form_submit_button("Add Researcher"):
        if not name or not email or not phone or not role or dept_id is None:
            st.warning("Please fill in all required fields.")
        else:
            try:
                run_dml("""
                    INSERT INTO RESEARCHER (ResearcherID, Name, Email, Phone, Role, Status, DeptID)
                    VALUES (:1, :2, :3, :4, :5, :6, :7)
                """, [int(r_id), name, email, phone, role, status, int(dept_id)])
                st.success("Researcher added successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Delete Researcher")
    selected_id = st.selectbox("Select Researcher to edit/delete", df["RESEARCHERID"],
                               format_func=lambda x: f"ID {x}: {df.set_index('RESEARCHERID').loc[x, 'NAME']}")
    row = df[df["RESEARCHERID"] == selected_id].iloc[0]

    col_u1, col_u2 = st.columns(2)
    with col_u1:
        edit_name = st.text_input("Edit Name", row["NAME"])
        edit_email = st.text_input("Edit Email", row["EMAIL"])
        edit_phone = st.text_input("Edit Phone", row["PHONE"])
    with col_u2:
        edit_role = st.text_input("Edit Role", row["ROLE"])
        edit_status = st.selectbox("Edit Status", ["ACTIVE", "INACTIVE"],
                                   index=0 if row["STATUS"] == "ACTIVE" else 1)
        if depts is not None and not depts.empty:
            curr_dept_idx = list(depts["DEPTID"]).index(row["DEPTID"]) if row["DEPTID"] in list(depts["DEPTID"]) else 0
            edit_dept = st.selectbox("Edit Department", options=depts["DEPTID"],
                                     index=curr_dept_idx,
                                     format_func=lambda x: f"{x} - {dept_map.get(x, '')}")
        else:
            edit_dept = row["DEPTID"]

    col1, col2 = st.columns(2)
    if col1.button("Update Researcher"):
        try:
            run_dml("""
                UPDATE RESEARCHER
                SET Name = :1, Email = :2, Phone = :3, Role = :4, Status = :5, DeptID = :6
                WHERE ResearcherID = :7
            """, [edit_name, edit_email, edit_phone, edit_role, edit_status, int(edit_dept), int(selected_id)])
            st.success("Researcher updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col2.button("Delete Researcher"):
        try:
            run_dml("DELETE FROM RESEARCHER WHERE ResearcherID = :1", [int(selected_id)])
            st.success("Researcher deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

