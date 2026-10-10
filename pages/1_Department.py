import streamlit as st
from db import run_query, run_dml, render_sidebar_reset

render_sidebar_reset()

st.title("🏢 Department Management")

# READ
try:
    df = run_query("SELECT * FROM DEPARTMENT ORDER BY DeptID")
    st.subheader("Department Records")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch departments: {e}")
    df = None

# CREATE
st.subheader("Add New Department")
with st.form("add_department"):
    dept_id = st.number_input("Dept ID", min_value=1, step=1)
    name = st.text_input("Department Name")
    building = st.text_input("Building")
    if st.form_submit_button("Add Department"):
        if not name or not building:
            st.warning("Please provide Department Name and Building.")
        else:
            try:
                run_dml("INSERT INTO DEPARTMENT (DeptID, DepartmentName, Building) VALUES (:1, :2, :3)",
                        [int(dept_id), name, building])
                st.success("Department added successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Delete Department")
    selected = st.selectbox("Select DeptID to edit/delete", df["DEPTID"])
    row = df[df["DEPTID"] == selected].iloc[0]
    new_name = st.text_input("Edit Name", row["DEPARTMENTNAME"])
    new_building = st.text_input("Edit Building", row["BUILDING"])
    col1, col2 = st.columns(2)
    if col1.button("Update Department"):
        try:
            run_dml("UPDATE DEPARTMENT SET DepartmentName = :1, Building = :2 WHERE DeptID = :3",
                    [new_name, new_building, int(selected)])
            st.success("Department updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if col2.button("Delete Department"):
        try:
            run_dml("DELETE FROM DEPARTMENT WHERE DeptID = :1", [int(selected)])
            st.success("Department deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

