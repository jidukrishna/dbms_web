import streamlit as st
import oracledb
import pandas as pd
import warnings
import subprocess
import os

warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

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

def call_proc(proc_name, params=None):
    """Executes a PL/SQL stored procedure with automatic commit."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        result = cur.callproc(proc_name, params or [])
        conn.commit()
        return result
    finally:
        cur.close()

def call_func(func_name, return_type, params=None):
    """Calls a PL/SQL function and returns the typed result."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        return cur.callfunc(func_name, return_type, params or [])
    finally:
        cur.close()

def call_proc_with_output(proc_name, params=None):
    """Executes a PL/SQL procedure and retrieves DBMS_OUTPUT buffer lines."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.callproc("DBMS_OUTPUT.ENABLE")
        cur.callproc(proc_name, params or [])
        lines = []
        line_var = cur.var(oracledb.STRING)
        status_var = cur.var(oracledb.NUMBER)
        while True:
            cur.callproc("DBMS_OUTPUT.GET_LINE", (line_var, status_var))
            if status_var.getvalue() != 0:
                break
            lines.append(line_var.getvalue())
        return lines
    finally:
        cur.close()

def _parse_sql_script(filepath):
    """Parses a SQL*Plus script into runnable SQL and PL/SQL blocks."""
    with open(filepath, 'r') as f:
        content = f.read()

    cleaned_lines = []
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith('PROMPT') or trimmed.startswith('SET ') or trimmed.startswith('SET\t'):
            continue
        cleaned_lines.append(line)

    content = '\n'.join(cleaned_lines)
    blocks = []
    current_block = []
    in_plsql = False

    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith('--') and not in_plsql:
            continue

        upper = trimmed.upper()
        if not in_plsql and (upper.startswith('CREATE OR REPLACE') or upper.startswith('BEGIN') or upper.startswith('DECLARE')):
            in_plsql = True

        if in_plsql:
            if trimmed == '/':
                stmt = '\n'.join(current_block).strip()
                if stmt:
                    blocks.append(('PLSQL', stmt))
                current_block = []
                in_plsql = False
            else:
                current_block.append(line)
        else:
            current_block.append(line)
            if trimmed.endswith(';'):
                stmt = '\n'.join(current_block).strip()
                if stmt.endswith(';'):
                    stmt = stmt[:-1].strip()
                if stmt and not stmt.startswith('--'):
                    blocks.append(('SQL', stmt))
                current_block = []

    return blocks

def reset_database_from_file(filepath="new.txt"):
    """
    Resets the database using the SQL*Plus script in filepath (new.txt).
    First attempts native sqlplus inside podman/docker container for exact script fidelity.
    Falls back to pure-Python DBAPI parser & executor if container CLI is not accessible.
    Returns (success: bool, message: str, log_output: str).
    """
    target_path = filepath
    if not os.path.exists(target_path):
        target_path = os.path.join(os.path.dirname(__file__), filepath)
        if not os.path.exists(target_path):
            return False, f"Reset script '{filepath}' not found.", ""

    with open(target_path, "r") as f:
        sql_content = f.read()

    user = st.secrets["oracle"]["user"]
    pw = st.secrets["oracle"]["password"]
    dsn = st.secrets["oracle"]["dsn"]

    # Engine 1: Native SQL*Plus via Podman/Docker
    for container_runtime in ["podman", "docker"]:
        try:
            cmd = [
                container_runtime, "exec", "-i", "oracle-db",
                "sqlplus", "-s", f"{user}/{pw}@localhost:1521/FREEPDB1"
            ]
            proc = subprocess.run(
                cmd,
                input=sql_content + "\nEXIT;\n",
                capture_output=True,
                text=True,
                timeout=60
            )
            if proc.returncode == 0:
                st.cache_resource.clear()
                return True, "Database successfully reset to new.txt using Oracle SQL*Plus!", proc.stdout
        except Exception:
            pass

    # Engine 2: Pure Python DBAPI Parser & Executor Fallback
    try:
        blocks = _parse_sql_script(target_path)
        conn = get_connection()
        cur = conn.cursor()
        executed_count = 0
        for btype, stmt in blocks:
            if stmt.upper().startswith("SELECT") and btype == "SQL":
                continue
            try:
                cur.execute(stmt)
                executed_count += 1
            except Exception:
                if "DROP" not in stmt.upper():
                    pass
        conn.commit()
        cur.close()
        st.cache_resource.clear()
        return True, f"Database reset successfully! ({executed_count} statements executed via DBAPI)", ""
    except Exception as e:
        return False, f"Failed to reset database: {e}", ""

def render_sidebar_reset():
    """Renders a convenient Auto-Reset button in the Streamlit sidebar."""
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ Database Controls")
        st.caption("Reset schema, procedures, and sample data from `new.txt`.")
        if st.button("🔄 Auto-Reset DB (new.txt)", key="btn_sidebar_reset", use_container_width=True, type="primary"):
            with st.spinner("Resetting database with new.txt..."):
                success, msg, _ = reset_database_from_file("new.txt")
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
