# Research Laboratory Equipment Booking — Streamlit App
## Implementation Plan (Simple / Presentation Version)

Goal: a working demo, not a production app. Keep every page short, avoid extra safety layers,
skip edge-case handling unless it's needed to show off a feature (like the booking conflict
check, since that's the interesting part of the schema). Build phases in order.

---

## 0. Tech Stack (minimal)

```
streamlit
python-oracledb
pandas
Pillow
```
Drop `qrcode` — a plain text/table receipt image is enough, no QR code needed.

---

## 1. Project Structure

```
lab_booking_app/
├── app.py                  # Home page: title + a couple of st.metric numbers
├── db.py                   # One connection function + run_query/run_dml
├── pages/
│   ├── 1_Department.py
│   ├── 2_Researcher.py
│   ├── 3_Equipment_Category.py
│   ├── 4_Equipment.py
│   ├── 5_Technician.py
│   ├── 6_Booking.py
│   ├── 7_Usage_Log.py
│   ├── 8_Maintenance.py
│   └── 9_Receipt.py
├── requirements.txt
└── .streamlit/secrets.toml
```

No `utils/` folder needed — put the small receipt function directly in `9_Receipt.py`.
Fewer files = easier to explain in a demo.

---

## 2. `db.py` — keep it to ~3 functions

```python
import streamlit as st
import oracledb
import pandas as pd

@st.cache_resource
def get_connection():
    return oracledb.connect(
        user=st.secrets["oracle"]["user"],
        password=st.secrets["oracle"]["password"],
        dsn=st.secrets["oracle"]["dsn"],
    )

def run_query(sql, params=None):
    conn = get_connection()
    return pd.read_sql(sql, conn, params=params)

def run_dml(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or {})
    conn.commit()
```

No separate `call_proc`/`call_func` wrappers — just call `cursor.callproc(...)` directly inside
the Booking page where it's needed. No custom exception handling layer — let Streamlit show the
raw error with a plain `try/except` + `st.error(e)` where it matters (only on Booking create).

---

## 3. One CRUD Page Template (reuse for every entity, copy-paste style)

Every simple entity page (Department, Equipment_Category, Technician, Researcher, Equipment,
Maintenance) follows this exact shape — no separate helper module, just repeat the pattern:

```python
import streamlit as st
from db import run_query, run_dml

st.title("Department")

# READ
df = run_query("SELECT * FROM DEPARTMENT ORDER BY DeptID")
st.dataframe(df)

# CREATE
with st.form("add"):
    dept_id = st.number_input("Dept ID", step=1)
    name = st.text_input("Department Name")
    building = st.text_input("Building")
    if st.form_submit_button("Add"):
        run_dml("INSERT INTO DEPARTMENT VALUES (:1,:2,:3)", [dept_id, name, building])
        st.rerun()

# UPDATE / DELETE
selected = st.selectbox("Select DeptID to edit/delete", df["DEPTID"])
row = df[df["DEPTID"] == selected].iloc[0]
new_name = st.text_input("Edit Name", row["DEPARTMENTNAME"])
new_building = st.text_input("Edit Building", row["BUILDING"])
col1, col2 = st.columns(2)
if col1.button("Update"):
    run_dml("UPDATE DEPARTMENT SET DepartmentName=:1, Building=:2 WHERE DeptID=:3",
            [new_name, new_building, selected])
    st.rerun()
if col2.button("Delete"):
    run_dml("DELETE FROM DEPARTMENT WHERE DeptID=:1", [selected])
    st.rerun()
```

Skip: search/filter boxes, delete-confirmation checkboxes, custom FK-violation messages.
If a delete fails because of an FK constraint, the raw Oracle error is fine for a demo — just
wrap in a basic `try/except` so the app doesn't crash:

```python
try:
    run_dml(...)
except Exception as e:
    st.error(str(e))
```

For **Researcher** and **Equipment** pages, the only difference from the template is that the
FK field is a `st.selectbox` built from the parent table instead of a text/number input:

```python
depts = run_query("SELECT DeptID, DepartmentName FROM DEPARTMENT")
dept_id = st.selectbox("Department", depts["DEPTID"], format_func=lambda x: depts.set_index("DEPTID").loc[x,"DEPARTMENTNAME"])
```

---

## 4. Booking Page — the one page worth extra effort

This is the schema's "interesting" feature (conflict detection), so it's the one page where
we keep the logic rather than simplifying it away.

```python
import streamlit as st
from db import get_connection, run_query

st.title("Booking")

df = run_query("""
    SELECT b.BookingID, r.Name Researcher, e.Name Equipment,
           b.BookingDate, b.StartTime, b.EndTime, b.Status
    FROM BOOKING b
    JOIN RESEARCHER r ON r.ResearcherID=b.ResearcherID
    JOIN EQUIPMENT e ON e.EquipmentID=b.EquipmentID
    ORDER BY b.BookingDate
""")
st.dataframe(df)

researchers = run_query("SELECT ResearcherID, Name FROM RESEARCHER")
equipment = run_query("SELECT EquipmentID, Name FROM EQUIPMENT")

with st.form("book"):
    r_id = st.selectbox("Researcher", researchers["RESEARCHERID"],
                         format_func=lambda x: researchers.set_index("RESEARCHERID").loc[x,"NAME"])
    e_id = st.selectbox("Equipment", equipment["EQUIPMENTID"],
                         format_func=lambda x: equipment.set_index("EQUIPMENTID").loc[x,"NAME"])
    date = st.date_input("Date")
    start = st.time_input("Start")
    end = st.time_input("End")
    purpose = st.text_area("Purpose")
    if st.form_submit_button("Book"):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.callproc("CREATE_BOOKING", [r_id, e_id, date,
                          start.strftime("%H:%M"), end.strftime("%H:%M"), purpose])
            conn.commit()
            st.success("Booked!")
            st.rerun()
        except Exception as e:
            st.error(str(e))   # shows ORA-20003 conflict message as-is — fine for demo
```

Cancel = just change Status to CANCELLED with a plain UPDATE, same as any other field edit.
No separate hard-delete-vs-cancel logic needed.

---

## 5. Usage_Log page

Just insert + display — no editing of the virtual `UsageHours` column (Oracle computes it).

```python
bookings = run_query("SELECT BookingID FROM BOOKING")
with st.form("log"):
    booking_id = st.selectbox("Booking", bookings["BOOKINGID"])
    start_dt = st.text_input("Actual Start (YYYY-MM-DD HH:MM)")
    end_dt = st.text_input("Actual End (YYYY-MM-DD HH:MM, optional)")
    if st.form_submit_button("Log"):
        run_dml("""INSERT INTO USAGE_LOG (UsageID, BookingID, ActualStartTime, ActualEndTime)
                   VALUES (USAGE_SEQ.NEXTVAL, :1, TO_DATE(:2,'YYYY-MM-DD HH24:MI'),
                           TO_DATE(:3,'YYYY-MM-DD HH24:MI'))""",
                [booking_id, start_dt, end_dt or None])
        st.rerun()

st.dataframe(run_query("SELECT * FROM USAGE_LOG ORDER BY UsageID"))
```

Plain text inputs for datetime instead of separate date+time pickers — less code, fine for a demo.

---

## 6. Home Page (`app.py`) — a few numbers, nothing more

```python
import streamlit as st
from db import run_query

st.title("Lab Equipment Booking — Dashboard")

c1, c2, c3 = st.columns(3)
c1.metric("Total Equipment", run_query("SELECT COUNT(*) N FROM EQUIPMENT")["N"][0])
c2.metric("Active Bookings", run_query("SELECT COUNT(*) N FROM BOOKING WHERE Status='CONFIRMED'")["N"][0])
c3.metric("Researchers", run_query("SELECT COUNT(*) N FROM RESEARCHER")["N"][0])
```

Drop the "equipment with no bookings" / "top maintenance cost" tables from the dashboard —
those already exist as pages (Equipment, Maintenance), no need to repeat them here.

---

## 7. Receipt Page — plain text on an image, no QR code

```python
import streamlit as st
from PIL import Image, ImageDraw
from db import run_query
import io

st.title("Booking Receipt")

df = run_query("""
    SELECT b.BookingID, r.Name Researcher, e.Name Equipment,
           b.BookingDate, b.StartTime, b.EndTime, b.Purpose, b.Status
    FROM BOOKING b JOIN RESEARCHER r ON r.ResearcherID=b.ResearcherID
    JOIN EQUIPMENT e ON e.EquipmentID=b.EquipmentID
""")
booking_id = st.selectbox("Select Booking", df["BOOKINGID"])
row = df[df["BOOKINGID"] == booking_id].iloc[0]

if st.button("Generate Receipt"):
    img = Image.new("RGB", (500, 400), "white")
    draw = ImageDraw.Draw(img)
    lines = [
        "LAB EQUIPMENT BOOKING RECEIPT",
        "-" * 30,
        f"Booking ID: {row['BOOKINGID']}",
        f"Researcher: {row['RESEARCHER']}",
        f"Equipment: {row['EQUIPMENT']}",
        f"Date: {row['BOOKINGDATE']}",
        f"Time: {row['STARTTIME']} - {row['ENDTIME']}",
        f"Purpose: {row['PURPOSE']}",
        f"Status: {row['STATUS']}",
    ]
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black")
        y += 30

    st.image(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.download_button("Download", buf.getvalue(), file_name="receipt.png")
```

`ImageFont.load_default()` is fine (skip custom `.ttf` fonts) — one less file to manage.

---

## 8. Build Order

1. `db.py`
2. Department, Equipment_Category, Technician (copy-paste the template 3x)
3. Researcher, Equipment (template + FK selectbox)
4. Booking
5. Usage_Log, Maintenance
6. Home dashboard
7. Receipt page

Each page is small enough to build and show in a few minutes — good for a live walkthrough.
