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
    try:
        cur.execute(sql, params or {})
        conn.commit()
    finally:
        cur.close()

