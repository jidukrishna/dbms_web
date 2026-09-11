import streamlit as st
from db import run_query, run_dml

st.title("🏷️ Equipment Category Management")

# READ
try:
    df = run_query("SELECT * FROM EQUIPMENT_CATEGORY ORDER BY CategoryID")
    st.subheader("Equipment Categories")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch categories: {e}")
    df = None

# CREATE
st.subheader("Add New Category")
with st.form("add_category"):
    cat_id = st.number_input("Category ID", min_value=1, step=1)
    name = st.text_input("Category Name")
    description = st.text_area("Description")
    if st.form_submit_button("Add Category"):
        if not name:
            st.warning("Please provide a category name.")
        else:
            try:
                run_dml("INSERT INTO EQUIPMENT_CATEGORY (CategoryID, Name, Description) VALUES (:1, :2, :3)",
                        [int(cat_id), name, description])
                st.success("Category added successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Delete Category")
    selected_id = st.selectbox("Select Category to edit/delete", df["CATEGORYID"],
                               format_func=lambda x: f"ID {x}: {df.set_index('CATEGORYID').loc[x, 'NAME']}")
    row = df[df["CATEGORYID"] == selected_id].iloc[0]
    new_name = st.text_input("Edit Category Name", row["NAME"])
    new_desc = st.text_area("Edit Description", row["DESCRIPTION"] or "")

    col1, col2 = st.columns(2)
    if col1.button("Update Category"):
        try:
            run_dml("UPDATE EQUIPMENT_CATEGORY SET Name = :1, Description = :2 WHERE CategoryID = :3",
                    [new_name, new_desc, int(selected_id)])
            st.success("Category updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col2.button("Delete Category"):
        try:
            run_dml("DELETE FROM EQUIPMENT_CATEGORY WHERE CategoryID = :1", [int(selected_id)])
            st.success("Category deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

