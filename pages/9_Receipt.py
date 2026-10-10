import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from db import run_query, render_sidebar_reset
import io
import datetime

render_sidebar_reset()

st.title("🧾 Booking Receipt Generator")
st.caption("Generate an official lab booking receipt image and export as PNG.")

try:
    df = run_query("""
        SELECT b.BookingID, r.Name AS Researcher, e.Name AS Equipment,
               TO_CHAR(b.BookingDate, 'YYYY-MM-DD') AS BookingDate,
               b.StartTime, b.EndTime, b.Purpose, b.Status
        FROM BOOKING b
        JOIN RESEARCHER r ON r.ResearcherID = b.ResearcherID
        JOIN EQUIPMENT e ON e.EquipmentID = b.EquipmentID
        ORDER BY b.BookingDate DESC, b.BookingID DESC
    """)
except Exception as e:
    st.error(f"Failed to fetch bookings: {e}")
    df = None

if df is not None and not df.empty:
    b_map = {
        row["BOOKINGID"]: f"Booking #{row['BOOKINGID']} - {row['RESEARCHER']} ({row['EQUIPMENT']}) [{row['STATUS']}]"
        for _, row in df.iterrows()
    }
    booking_id = st.selectbox(
        "Select Booking for Receipt",
        options=list(df["BOOKINGID"]),
        format_func=lambda x: b_map.get(x, f"Booking #{x}")
    )
    row = df[df["BOOKINGID"] == booking_id].iloc[0]

    st.info(f"Generating receipt for Booking **#{row['BOOKINGID']}** ({row['RESEARCHER']} - {row['EQUIPMENT']})")

    if st.button("Generate Receipt Image", type="primary"):
        width, height = 540, 420
        img = Image.new("RGB", (width, height), color="#FAFAFA")
        draw = ImageDraw.Draw(img)

        # Border
        draw.rectangle([(8, 8), (width - 8, height - 8)], outline="#333333", width=2)
        draw.rectangle([(12, 12), (width - 12, height - 12)], outline="#666666", width=1)

        font = ImageFont.load_default()

        lines = [
            "================================================",
            "   RESEARCH LABORATORY EQUIPMENT BOOKING RECEIPT",
            "================================================",
            f" Receipt Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "------------------------------------------------",
            f" Booking ID   : {row['BOOKINGID']}",
            f" Researcher   : {row['RESEARCHER']}",
            f" Equipment    : {row['EQUIPMENT']}",
            f" Booking Date : {row['BOOKINGDATE']}",
            f" Time Slot    : {row['STARTTIME']} - {row['ENDTIME']}",
            f" Status       : {row['STATUS']}",
            f" Purpose      : {row['PURPOSE']}",
            "------------------------------------------------",
            " Authorized by Laboratory Management System",
            " Please present this receipt to the technician.",
            "================================================"
        ]

        y = 25
        for line in lines:
            draw.text((25, y), line, fill="#111111", font=font)
            y += 22

        st.image(img, caption=f"Receipt #{row['BOOKINGID']}", use_container_width=False)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.download_button(
            label=f"📥 Download Receipt #{row['BOOKINGID']} (PNG)",
            data=buf.getvalue(),
            file_name=f"receipt_booking_{row['BOOKINGID']}.png",
            mime="image/png"
        )
else:
    st.warning("No booking records found to generate receipt.")

