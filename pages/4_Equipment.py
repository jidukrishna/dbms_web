import streamlit as st
import datetime
from db import run_query, run_dml, render_sidebar_reset

render_sidebar_reset()

st.title("⚙️ Equipment Management")

# READ
try:
    df = run_query("""
        SELECT e.EquipmentID, e.Name, e.Model, e.Manufacturer, e.SerialNumber,
               e.PurchaseDate, e.Location, e.Cost, e.Status, e.CategoryID,
               c.Name AS CategoryName
        FROM EQUIPMENT e
        JOIN EQUIPMENT_CATEGORY c ON c.CategoryID = e.CategoryID
        ORDER BY e.EquipmentID
    """)
    st.subheader("Equipment Inventory")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to fetch equipment: {e}")
    df = None

# Categories for FK dropdown
try:
    cats = run_query("SELECT CategoryID, Name FROM EQUIPMENT_CATEGORY ORDER BY CategoryID")
    cat_map = dict(zip(cats["CategoryID"], cats["NAME"])) if "CategoryID" in cats.columns else dict(zip(cats["CATEGORYID"], cats["NAME"]))
except Exception as e:
    cats = None
    cat_map = {}

status_options = ['AVAILABLE', 'BOOKED', 'MAINTENANCE', 'RETIRED']

# CREATE
st.subheader("Add New Equipment")
with st.form("add_equipment"):
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        e_id = st.number_input("Equipment ID", min_value=1, step=1)
        name = st.text_input("Equipment Name")
        model = st.text_input("Model")
        manufacturer = st.text_input("Manufacturer")
        serial_no = st.text_input("Serial Number (Unique)")
    with col_a2:
        purchase_date = st.date_input("Purchase Date", value=datetime.date.today())
        location = st.text_input("Lab Location")
        cost = st.number_input("Cost (INR)", min_value=0.0, step=1000.0)
        status = st.selectbox("Status", status_options)
        if cats is not None and not cats.empty:
            cat_keys = list(cats["CATEGORYID"] if "CATEGORYID" in cats.columns else cats["CategoryID"])
            cat_id = st.selectbox(
                "Category",
                options=cat_keys,
                format_func=lambda x: f"{x} - {cat_map.get(x, '')}"
            )
        else:
            cat_id = None
            st.warning("No categories found. Please create a category first.")

    if st.form_submit_button("Add Equipment"):
        if not name or not serial_no or not location or cat_id is None:
            st.warning("Please fill in all required fields (Name, Serial Number, Location, Category).")
        else:
            try:
                run_dml("""
                    INSERT INTO EQUIPMENT
                    (EquipmentID, Name, Model, Manufacturer, SerialNumber, PurchaseDate, Location, Cost, Status, CategoryID)
                    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
                """, [int(e_id), name, model, manufacturer, serial_no, purchase_date, location, float(cost), status, int(cat_id)])
                st.success("Equipment registered successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# UPDATE / DELETE
if df is not None and not df.empty:
    st.subheader("Edit or Delete Equipment")
    selected_id = st.selectbox("Select Equipment to edit/delete", df["EQUIPMENTID"],
                               format_func=lambda x: f"ID {x}: {df.set_index('EQUIPMENTID').loc[x, 'NAME']}")
    row = df[df["EQUIPMENTID"] == selected_id].iloc[0]

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        edit_name = st.text_input("Edit Name", row["NAME"])
        edit_model = st.text_input("Edit Model", row["MODEL"] or "")
        edit_mfr = st.text_input("Edit Manufacturer", row["MANUFACTURER"] or "")
        edit_serial = st.text_input("Edit Serial Number", row["SERIALNUMBER"])
    with col_e2:
        curr_pdate = row["PURCHASEDATE"]
        if isinstance(curr_pdate, str):
            try:
                curr_pdate = datetime.date.fromisoformat(curr_pdate[:10])
            except Exception:
                curr_pdate = datetime.date.today()
        elif hasattr(curr_pdate, 'date'):
            curr_pdate = curr_pdate.date()
        edit_pdate = st.date_input("Edit Purchase Date", value=curr_pdate or datetime.date.today())
        edit_loc = st.text_input("Edit Location", row["LOCATION"])
        edit_cost = st.number_input("Edit Cost", value=float(row["COST"] or 0.0), min_value=0.0)
        curr_status_idx = status_options.index(row["STATUS"]) if row["STATUS"] in status_options else 0
        edit_status = st.selectbox("Edit Status", status_options, index=curr_status_idx)

        if cats is not None and not cats.empty:
            cat_keys = list(cats["CATEGORYID"] if "CATEGORYID" in cats.columns else cats["CategoryID"])
            curr_cat_idx = cat_keys.index(row["CATEGORYID"]) if row["CATEGORYID"] in cat_keys else 0
            edit_cat = st.selectbox("Edit Category", cat_keys, index=curr_cat_idx,
                                    format_func=lambda x: f"{x} - {cat_map.get(x, '')}")
        else:
            edit_cat = row["CATEGORYID"]

    col1, col2 = st.columns(2)
    if col1.button("Update Equipment"):
        try:
            run_dml("""
                UPDATE EQUIPMENT
                SET Name = :1, Model = :2, Manufacturer = :3, SerialNumber = :4,
                    PurchaseDate = :5, Location = :6, Cost = :7, Status = :8, CategoryID = :9
                WHERE EquipmentID = :10
            """, [edit_name, edit_model, edit_mfr, edit_serial, edit_pdate, edit_loc, float(edit_cost), edit_status, int(edit_cat), int(selected_id)])
            st.success("Equipment updated successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if col2.button("Delete Equipment"):
        try:
            run_dml("DELETE FROM EQUIPMENT WHERE EquipmentID = :1", [int(selected_id)])
            st.success("Equipment deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

