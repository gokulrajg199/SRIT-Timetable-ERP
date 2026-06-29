
import streamlit as st
import sqlite3
import pandas as pd
import random
from io import BytesIO
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text as sql_text

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

DB_NAME = "timetable.db"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PERIODS = [
    (1, "08:50 AM - 09:40 AM"),
    (2, "09:40 AM - 10:30 AM"),
    (3, "10:50 AM - 11:40 AM"),
    (4, "11:40 AM - 12:30 PM"),
    (5, "01:20 PM - 02:10 PM"),
    (6, "02:10 PM - 03:00 PM"),
    (7, "03:15 PM - 04:05 PM"),
    (8, "04:05 PM - 04:55 PM"),
]
PERIOD_DICT = dict(PERIODS)

st.set_page_config(
    page_title="Sri Ramakrishna Institute of Technology - Timetable ERP",
    page_icon="🏫",
    layout="wide"
)

CUSTOM_CSS = """
<style>
.stApp{
    background:linear-gradient(135deg,#f4fbf6 0%,#eef8f0 45%,#ffffff 100%);
    color:#111111;
}

/* premium container spacing */
.block-container{
    padding-top:1.2rem;
    padding-bottom:2rem;
}

/* DASHBOARD CARDS */
.card{
    background:white !important;
    border:2px solid #d4af37 !important;
    border-radius:18px !important;
    box-shadow:0 5px 15px rgba(0,0,0,0.10) !important;
}

/* METRIC CARDS */
div[data-testid="stMetric"]{
    background:white !important;
    border:2px solid #d4af37 !important;
    border-left:6px solid #1b5e20 !important;
    border-radius:12px !important;
    padding:10px !important;
    min-height:80px !important;
}

div[data-testid="stMetricValue"]{
    font-size:28px !important;
    font-weight:800 !important;
    color:#1b5e20 !important;
}

/* sidebar premium */
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0f3d17,#1b5e20,#2e7d32);
    border-right:4px solid #d4af37;
}

section[data-testid="stSidebar"] *{
    color:white !important;
    font-weight:700 !important;
}

/* buttons */
.stButton button{
    background:linear-gradient(135deg,#1b5e20,#43a047);
    color:white !important;
    border:2px solid #d4af37;
    border-radius:14px;
    font-weight:800;
    box-shadow:0 6px 14px rgba(0,0,0,0.18);
    transition:all 0.25s ease;
}

.stButton button:hover{
    transform:translateY(-2px);
    box-shadow:0 10px 22px rgba(0,0,0,0.24);
    border-color:white;
}

/* headings */
h1,h2,h3{
    color:#1b5e20 !important;
    font-weight:900 !important;
    letter-spacing:0.3px;
}

/* metric numbers */
div[data-testid="stMetricValue"]{
    color:#1b5e20 !important;
    font-size:34px !important;
    font-weight:900 !important;
}

/* tables / grids */
table{
    width:100% !important;
    border-collapse:collapse !important;
    border-radius:12px !important;
    overflow:hidden !important;
}

th{
    background:#1b5e20 !important;
    color:white !important;
    text-align:center !important;
    font-size:19px !important;
    padding:13px !important;
    border:1px solid #d4af37 !important;
}

td{
    text-align:center !important;
    font-size:17px !important;
    font-weight:700 !important;
    padding:12px !important;
    border:1px solid #d4af37 !important;
}

/* dataframe readability */
div[data-testid="stDataFrame"]{
    border-radius:16px;
    overflow:hidden;
    box-shadow:0 6px 18px rgba(0,0,0,0.10);
}

/* inputs */
input, textarea{
    border-radius:10px !important;
    font-size:17px !important;
}

/* info boxes */
div[data-testid="stAlert"]{
    border-radius:14px !important;
    box-shadow:0 4px 14px rgba(0,0,0,0.08);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================
# SUPABASE / POSTGRES TEST LAYER
# ==============================
def get_supabase_engine():
    try:
        database_url = st.secrets.get("DATABASE_URL", "")
        if not database_url:
            return None, "DATABASE_URL not found in Streamlit Secrets."
        engine = create_engine(database_url, pool_pre_ping=True)
        return engine, None
    except Exception as e:
        return None, str(e)


def supabase_query_df(query):
    engine, err = get_supabase_engine()
    if err:
        raise Exception(err)
    with engine.connect() as conn:
        return pd.read_sql(sql_text(query), conn)


def supabase_test_page():
    header()
    st.subheader("Supabase Cloud Database Test")

    st.info("This page checks whether Streamlit can connect to your Supabase PostgreSQL database using DATABASE_URL from Secrets.")

    try:
        users = supabase_query_df("SELECT id, username, role, name, department, is_active FROM users ORDER BY id")
        st.success("Connected to Supabase successfully.")
        st.dataframe(users, use_container_width=True, hide_index=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Users", len(users))
        c2.metric("Admin", len(users[users['role'] == 'Admin']) if 'role' in users else 0)
        c3.metric("HOD", len(users[users['role'] == 'HOD']) if 'role' in users else 0)
        c4.metric("Faculty", len(users[users['role'] == 'Faculty']) if 'role' in users else 0)

    except Exception as e:
        st.error("Supabase connection failed.")
        st.code(str(e))
        st.warning("Check Streamlit Secrets, requirements.txt, and your Supabase DATABASE_URL.")

def connect_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def execute(query, params=()):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(query, params)

    cur.executemany(
        "INSERT OR IGNORE INTO departments(department_name, hod_name, status) VALUES(?,?,?)",
        [
            ("CSE", "HOD CSE", "Active"),
            ("IT", "HOD IT", "Active"),
            ("AI&DS", "HOD AI&DS", "Active"),
            ("ECE", "HOD ECE", "Active"),
            ("EEE", "HOD EEE", "Active"),
            ("MECH", "HOD MECH", "Active"),
        ]
    )

    cur.executemany(
        "INSERT OR IGNORE INTO users(username, password, role, name, department) VALUES(?,?,?,?,?)",
        [
            ("admin", "admin123", "Admin", "System Admin", "Administration"),
            ("principal", "principal123", "Principal", "Principal", "Administration"),
            ("cse_coord", "cse123", "Coordinator", "CSE Timetable Coordinator", "CSE"),
            ("it_coord", "it123", "Coordinator", "IT Timetable Coordinator", "IT"),
            ("aids_coord", "aids123", "Coordinator", "AI&DS Timetable Coordinator", "AI&DS"),
            ("ece_coord", "ece123", "Coordinator", "ECE Timetable Coordinator", "ECE"),
            ("eee_coord", "eee123", "Coordinator", "EEE Timetable Coordinator", "EEE"),
            ("mech_coord", "mech123", "Coordinator", "MECH Timetable Coordinator", "MECH"),
            ("cse_hod", "hod123", "HOD", "CSE HOD", "CSE"),
            ("it_hod", "hod123", "HOD", "IT HOD", "IT"),
            ("aids_hod", "hod123", "HOD", "AI&DS HOD", "AI&DS"),
            ("ece_hod", "hod123", "HOD", "ECE HOD", "ECE"),
            ("eee_hod", "hod123", "HOD", "EEE HOD", "EEE"),
            ("mech_hod", "hod123", "HOD", "MECH HOD", "MECH"),
            ("hod", "hod123", "HOD", "HOD User", "CSE"),
            ("faculty", "faculty123", "Faculty", "Faculty User", "CSE"),
            ("student", "student123", "Student", "Student User", "CSE"),
        ]
    )

    cur.execute(
        "INSERT OR IGNORE INTO academic_years(year_name, semester_type, is_active) VALUES(?,?,?)",
        ("2026-2027", "Odd Semester", 1)
    )
    conn.commit()
    conn.close()

def execute_many(query, values):
    conn = connect_db()
    cur = conn.cursor()
    cur.executemany(query, values)
    conn.commit()
    conn.close()


def query_df(query, params=()):
    conn = connect_db()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def current_department():
    return st.session_state.get("department", "")

def current_role():
    return st.session_state.get("role", "")

def can_view_all_departments():
    return current_role() in ["Admin", "Principal"]

def dept_filter_sql(alias=""):
    if can_view_all_departments():
        return "", ()
    prefix = f"{alias}." if alias else ""
    return f" AND {prefix}department=?", (current_department(),)


def log_action(action, details=""):
    try:
        username = st.session_state.get("username", "system")
        execute(
            "INSERT INTO audit_log(action, details, created_at, username) VALUES(?,?,?,?)",
            (action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username)
        )
    except Exception:
        pass


def column_exists(table, column):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()
    return column in cols


def add_col(table, column, definition):
    if not column_exists(table, column):
        execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        designation TEXT,
        department TEXT,
        max_hours INTEGER DEFAULT 24
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year TEXT,
        department TEXT NOT NULL,
        semester TEXT NOT NULL,
        section TEXT NOT NULL,
        working_days INTEGER DEFAULT 6,
        UNIQUE(year, department, semester, section)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT UNIQUE NOT NULL,
        room_type TEXT DEFAULT 'Classroom',
        capacity INTEGER DEFAULT 60,
        equipment TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_code TEXT,
        subject_name TEXT NOT NULL,
        subject_type TEXT DEFAULT 'Theory',
        weekly_hours INTEGER DEFAULT 0,
        theory_hours INTEGER DEFAULT 0,
        lab_hours INTEGER DEFAULT 0,
        theory_continuous_required INTEGER DEFAULT 0,
        theory_continuous_hours INTEGER DEFAULT 1,
        lab_continuous_required INTEGER DEFAULT 1,
        lab_continuous_hours INTEGER DEFAULT 4,
        faculty_id INTEGER NOT NULL,
        lab_faculty_id INTEGER,
        section_id INTEGER NOT NULL,
        room_id INTEGER,
        lab_room_id INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER,
        day TEXT,
        period INTEGER,
        timing TEXT,
        subject_id INTEGER,
        faculty_id INTEGER,
        room_id INTEGER,
        session_type TEXT DEFAULT 'Theory',
        block_label TEXT DEFAULT '',
        batch_label TEXT DEFAULT '',
        generated_at TEXT,
        entry_mode TEXT DEFAULT 'Auto'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty_unavailable(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        period INTEGER NOT NULL,
        reason TEXT DEFAULT '',
        UNIQUE(faculty_id, day, period)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty_preferences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER NOT NULL UNIQUE,
        preferred_day TEXT DEFAULT '',
        preferred_period INTEGER,
        avoid_last_period INTEGER DEFAULT 0,
        remarks TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name TEXT UNIQUE NOT NULL,
        hod_name TEXT DEFAULT '',
        status TEXT DEFAULT 'Active'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS academic_years(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year_name TEXT NOT NULL,
        semester_type TEXT NOT NULL,
        is_active INTEGER DEFAULT 0,
        UNIQUE(year_name, semester_type)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable_approvals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Draft',
        hod_comment TEXT DEFAULT '',
        principal_comment TEXT DEFAULT '',
        updated_at TEXT,
        UNIQUE(section_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        details TEXT,
        created_at TEXT,
        username TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT DEFAULT '',
        department TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty_swap_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER,
        request_details TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS faculty_leave(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_id INTEGER,
        day TEXT,
        period INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timetable_id INTEGER,
        attendance_date TEXT,
        status TEXT,
        remarks TEXT DEFAULT '',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_timetable(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER,
        subject_id INTEGER,
        exam_date TEXT,
        exam_time TEXT,
        room_id INTEGER
    )
    """)
    cur.execute("""
CREATE TABLE IF NOT EXISTS leave_alteration_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leave_id INTEGER,
    timetable_id INTEGER,
    original_faculty_id INTEGER,
    substitute_faculty_id INTEGER,
    day TEXT,
    period INTEGER,
    status TEXT DEFAULT 'Pending',
    hod_remark TEXT DEFAULT '',
    created_at TEXT
)
""")
    default_users = [
    ("admin", "admin123", "Admin", "Administrator", "Administration"),
    ("principal", "principal123", "Principal", "Principal", "Administration"),

    ("cse_coord", "cse123", "Coordinator", "CSE Coordinator", "CSE"),
    ("it_coord", "it123", "Coordinator", "IT Coordinator", "IT"),
    ("aids_coord", "aids123", "Coordinator", "AI&DS Coordinator", "AI&DS"),
    ("ece_coord", "ece123", "Coordinator", "ECE Coordinator", "ECE"),
    ("eee_coord", "eee123", "Coordinator", "EEE Coordinator", "EEE"),
    ("mech_coord", "mech123", "Coordinator", "MECH Coordinator", "MECH"),

    ("cse_hod", "hod123", "HOD", "CSE HOD", "CSE"),
    ("it_hod", "hod123", "HOD", "IT HOD", "IT"),
    ("aids_hod", "hod123", "HOD", "AI&DS HOD", "AI&DS"),
    ("ece_hod", "hod123", "HOD", "ECE HOD", "ECE"),
    ("eee_hod", "hod123", "HOD", "EEE HOD", "EEE"),
    ("mech_hod", "hod123", "HOD", "MECH HOD", "MECH"),
]

    cur.executemany("""
        INSERT OR IGNORE INTO users(username, password, role, name, department)
        VALUES(?,?,?,?,?)
    """, default_users)

    conn.commit()
    conn.close()

    add_col("sections", "year", "TEXT")
    add_col("rooms", "capacity", "INTEGER DEFAULT 60")
    add_col("rooms", "equipment", "TEXT DEFAULT ''")
    add_col("rooms", "department", "TEXT DEFAULT 'CSE'")

    add_col("subjects", "theory_hours", "INTEGER DEFAULT 0")
    add_col("subjects", "lab_hours", "INTEGER DEFAULT 0")
    add_col("subjects", "theory_continuous_required", "INTEGER DEFAULT 0")
    add_col("subjects", "theory_continuous_hours", "INTEGER DEFAULT 1")
    add_col("subjects", "same_day_theory", "INTEGER DEFAULT 0")
    add_col("subjects", "lab_continuous_required", "INTEGER DEFAULT 1")
    add_col("subjects", "lab_continuous_hours", "INTEGER DEFAULT 4")
    add_col("subjects", "lab_faculty_id", "INTEGER")
    add_col("subjects", "lab_room_id", "INTEGER")

    add_col("timetable", "session_type", "TEXT DEFAULT 'Theory'")
    add_col("timetable", "block_label", "TEXT DEFAULT ''")
    add_col("timetable", "entry_mode", "TEXT DEFAULT 'Auto'")

    add_col("faculty_preferences", "preferred_day", "TEXT DEFAULT ''")
    add_col("faculty_preferences", "preferred_period", "INTEGER")
    add_col("faculty_preferences", "avoid_last_period", "INTEGER DEFAULT 0")
    add_col("faculty_preferences", "remarks", "TEXT DEFAULT ''")

    add_col("sections", "academic_year", "TEXT DEFAULT '2026-2027'")
    add_col("sections", "semester_type", "TEXT DEFAULT 'Odd Semester'")
    add_col("sections", "is_published", "INTEGER DEFAULT 0")

    add_col("timetable_approvals", "status", "TEXT DEFAULT 'Draft'")
    add_col("timetable_approvals", "hod_comment", "TEXT DEFAULT ''")
    add_col("timetable_approvals", "principal_comment", "TEXT DEFAULT ''")
    add_col("timetable_approvals", "updated_at", "TEXT")

    add_col("exam_timetable", "exam_type", "TEXT DEFAULT 'CIA 1'")

def clean_int(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if value == "":
        return None
    return int(value)


def section_label_df():
    if can_view_all_departments():
        return query_df("""
            SELECT id,
                   COALESCE(year,'') || ' | ' || department || ' | Sem ' || semester || ' | Sec ' || section AS label,
                   working_days
            FROM sections
            ORDER BY year, department, semester, section
        """)
    return query_df("""
        SELECT id,
               COALESCE(year,'') || ' | ' || department || ' | Sem ' || semester || ' | Sec ' || section AS label,
               working_days
        FROM sections
        WHERE department=?
        ORDER BY year, semester, section
    """, (current_department(),))

def faculty_df():
    if can_view_all_departments():
        return query_df("SELECT id, name FROM faculty ORDER BY department, name")
    return query_df(
        "SELECT id, name FROM faculty WHERE department=? ORDER BY name",
        (current_department(),)
    )

def rooms_df(room_type=None):
    if can_view_all_departments():
        if room_type:
            return query_df(
                "SELECT id, room_name, room_type FROM rooms WHERE room_type=? ORDER BY department, room_name",
                (room_type,)
            )
        return query_df("SELECT id, room_name, room_type FROM rooms ORDER BY department, room_name")

    if room_type:
        return query_df(
            "SELECT id, room_name, room_type FROM rooms WHERE department=? AND room_type=? ORDER BY room_name",
            (current_department(), room_type)
        )
    return query_df(
        "SELECT id, room_name, room_type FROM rooms WHERE department=? ORDER BY room_name",
        (current_department(),)
    )

def subject_label_df(section_id=None):
    if section_id:
        return query_df(
            "SELECT id, subject_code || ' - ' || subject_name AS label FROM subjects WHERE section_id=? ORDER BY subject_name",
            (section_id,)
        )

    if can_view_all_departments():
        return query_df(
            "SELECT id, subject_code || ' - ' || subject_name AS label FROM subjects ORDER BY subject_name"
        )

    return query_df("""
        SELECT s.id, s.subject_code || ' - ' || s.subject_name AS label
        FROM subjects s
        JOIN sections sec ON s.section_id=sec.id
        WHERE sec.department=?
        ORDER BY s.subject_name
    """, (current_department(),))

def header():
    col1, col2, col3 = st.columns([1, 10, 1])

    with col2:
        st.markdown(
            """
            <div style="display:flex; justify-content:center;">
            """,
            unsafe_allow_html=True
        )

        st.image(
            "College_banner.png",
            use_container_width=True
        )

        st.markdown(
            """
            </div>
            """,
            unsafe_allow_html=True
        )
  
def login_page():
    header()

    st.markdown("""
    <div style="
        background:#ffffff;
        padding:18px;
        border-radius:14px;
        border-left:8px solid #1b5e20;
        border-right:3px solid #d4af37;
        margin-bottom:20px;
        box-shadow:0px 3px 12px rgba(0,0,0,0.12);
        text-align:center;
    ">
        <h2 style="color:#1b5e20; margin:0;">
            🏫 SRIT Academic Resource Management System (SARMS)
        </h2>
        <h4 style="color:#333333; margin-top:8px;">
            Smart Timetable, Approval & Academic Resource Platform
        </h4>
        <p style="font-size:17px; color:#555; margin-top:8px;">
            Faculty Management • Timetable Generation • Approval Workflow • Leave Management • Exam Scheduling • Student Portal
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.1, 1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Role Based Login")

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True):
            user_df = query_df(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, password)
            )

            if not user_df.empty:
                row = user_df.iloc[0]

                st.session_state.logged_in = True
                st.session_state.username = row["username"]
                st.session_state.role = row["role"]
                st.session_state.full_name = row["name"]
                st.session_state.department = row["department"]

                st.success(f"Welcome {row['name']} ({row['role']})")
                st.rerun()
            else:
                st.error("Invalid username or password")

        st.info(
            "Default logins: admin/admin123 | principal/principal123 | hod/hod123 | faculty/faculty123 | student/student123"
        )
        st.markdown("</div>", unsafe_allow_html=True)

def allocate_block(grid, day, start_period, length, session, used_faculty, used_room):
    slots = []
    for p in range(start_period, start_period + length):
        if p not in PERIOD_DICT:
            return False
        if grid.get((day, p)) is not None:
            return False
        if (day, p, session["faculty_id"]) in used_faculty:
            return False
        room_id = clean_int(session.get("room_id"))
        if room_id and (day, p, room_id) in used_room:
            return False
        slots.append((day, p))

    block = f"{session['session_type']}-{length}P"
    for d, p in slots:
        item = session.copy()
        item["block_label"] = block
        grid[(d, p)] = item
        used_faculty.add((d, p, session["faculty_id"]))
        room_id = clean_int(session.get("room_id"))
        if room_id:
            used_room.add((d, p, room_id))
    return True


def create_subject_sessions(subject):
    sessions = []
    stype = str(subject["subject_type"]).lower().strip()

    theory_hours = int(subject.get("theory_hours") or 0)
    lab_hours = int(subject.get("lab_hours") or 0)

    if stype == "theory":
        theory_hours = int(subject.get("weekly_hours") or theory_hours or 0)
    elif stype in ["lab", "practical"]:
        lab_hours = int(subject.get("weekly_hours") or lab_hours or 0)
    elif stype == "theory + lab":
        if theory_hours == 0 and lab_hours == 0:
            total = int(subject.get("weekly_hours") or 0)
            theory_hours = max(0, total - 2)
            lab_hours = min(2, total)

    if theory_hours > 0:
        sessions.append({
            "subject_id": int(subject["id"]),
            "subject_name": subject["subject_name"],
            "subject_code": subject.get("subject_code", ""),
            "session_type": "Theory",
            "hours": theory_hours,
            "continuous_required": int(subject.get("theory_continuous_required") or 0),
            "continuous_hours": max(1, int(subject.get("theory_continuous_hours") or 1)),
            "same_day_required": int(subject.get("same_day_theory") or 0),
            "faculty_id": int(subject["faculty_id"]),
            "room_id": clean_int(subject.get("room_id")),
        })

    if lab_hours > 0:
        sessions.append({
            "subject_id": int(subject["id"]),
            "subject_name": subject["subject_name"],
            "subject_code": subject.get("subject_code", ""),
            "session_type": "Lab",
            "hours": lab_hours,
            "continuous_required": 1,
            "continuous_hours": max(1, int(subject.get("lab_continuous_hours") or lab_hours or 1)),
            "same_day_required": 0,
            "faculty_id": int(subject.get("lab_faculty_id") or subject["faculty_id"]),
            "room_id": clean_int(subject.get("lab_room_id") or subject.get("room_id")),
        })

    return sessions


def generate_for_section(section_id, working_days=6, clear_old=True):
    days = DAYS[:working_days]
    subjects = query_df("SELECT * FROM subjects WHERE section_id=?", (section_id,)).to_dict("records")

    if not subjects:
        return False, "No subjects available for this section."

    if clear_old:
        execute("DELETE FROM timetable WHERE section_id=?", (section_id,))

    old = query_df("""
        SELECT day, period, faculty_id, room_id, subject_id, session_type
        FROM timetable
    """)

    used_faculty = set()
    used_room = set()
    faculty_day_theory = {}
    faculty_day_lab_count = {}
    section_day_subject_theory = {}
    section_day_subject_lab = set()

    unavailable_df = query_df("SELECT faculty_id, day, period FROM faculty_unavailable")
    unavailable_slots = set(
        (r.day, int(r.period), int(r.faculty_id))
        for r in unavailable_df.itertuples()
    )

    pref_df = query_df("SELECT faculty_id, preferred_day, preferred_period, avoid_last_period FROM faculty_preferences")
    faculty_preferences = {}
    for r in pref_df.itertuples():
        faculty_preferences[int(r.faculty_id)] = {
            "preferred_day": str(r.preferred_day or ""),
            "preferred_period": None if pd.isna(r.preferred_period) else int(r.preferred_period),
            "avoid_last_period": int(r.avoid_last_period or 0)
        }

    for r in old.itertuples():
        if pd.notna(r.faculty_id):
            fid = int(r.faculty_id)
            used_faculty.add((r.day, int(r.period), fid))
            if str(r.session_type).lower() == "lab":
                faculty_day_lab_count[(r.day, fid)] = faculty_day_lab_count.get((r.day, fid), 0) + 1
            else:
                faculty_day_theory[(r.day, fid)] = faculty_day_theory.get((r.day, fid), 0) + 1
        if pd.notna(r.room_id):
            used_room.add((r.day, int(r.period), int(r.room_id)))

    grid = {(d, p): None for d in days for p, _ in PERIODS}

    sessions = []
    for s in subjects:
        sessions.extend(create_subject_sessions(s))

    # Priority: lab / continuous / long blocks first
    sessions.sort(key=lambda x: (x["session_type"] == "Lab", x["continuous_required"], x["continuous_hours"]), reverse=True)

    def can_place(day, start, length, session):
        fid = int(session["faculty_id"])
        sid = int(session["subject_id"])
        room_id = clean_int(session.get("room_id"))
        is_lab = session["session_type"] == "Lab"

        # Same subject lab and theory should not be on same day for the same section.
        if is_lab and (day, sid) in section_day_subject_theory:
            return False
        if (not is_lab) and (day, sid) in section_day_subject_lab:
            return False

        # Same theory subject max 2 periods per day unless Same Day Theory is enabled.
        if not is_lab:
            current_same_subject = section_day_subject_theory.get((day, sid), 0)
            if not int(session.get("same_day_required") or 0):
                if current_same_subject + length > 2:
                    return False

        # Faculty daily rules.
        current_lab = faculty_day_lab_count.get((day, fid), 0)
        current_theory = faculty_day_theory.get((day, fid), 0)

        if is_lab:
            # Only one lab per faculty per day, maximum 4 lab hours.
            if current_lab > 0:
                return False
            if length > 4:
                return False
            # If faculty already has more than 2 theory hours that day, no lab.
            if current_theory > 2:
                return False
        else:
            # Faculty theory total max 3 per day across different subjects.
            # If faculty has lab on same day, theory max 2.
            limit = 2 if current_lab > 0 else 3
            if current_theory + length > limit:
                return False

        for p in range(start, start + length):
            if p not in PERIOD_DICT:
                return False
            pref = faculty_preferences.get(fid, {})
            if pref.get("avoid_last_period") and p == max(PERIOD_DICT.keys()):
                return False
            if grid.get((day, p)) is not None:
                return False
            if (day, p, fid) in used_faculty:
                return False
            if (day, p, fid) in unavailable_slots:
                return False
            if room_id:
                existing_room_clash = query_df("""
                    SELECT id FROM timetable
                    WHERE day=? AND period=? AND room_id=?
                """, (day, p, room_id))

                if not existing_room_clash.empty:
                    return False

                if (day, p, room_id) in used_room:
                    return False
        return True

    def place(day, start, length, session):
        fid = int(session["faculty_id"])
        sid = int(session["subject_id"])
        room_id = clean_int(session.get("room_id"))
        is_lab = session["session_type"] == "Lab"
        block = f"{session['session_type']}-{length}P"

        for p in range(start, start + length):
            item = session.copy()
            item["block_label"] = block
            grid[(day, p)] = item
            used_faculty.add((day, p, fid))
            if room_id:
                used_room.add((day, p, room_id))

        if is_lab:
            faculty_day_lab_count[(day, fid)] = faculty_day_lab_count.get((day, fid), 0) + 1
            section_day_subject_lab.add((day, sid))
        else:
            faculty_day_theory[(day, fid)] = faculty_day_theory.get((day, fid), 0) + length
            section_day_subject_theory[(day, sid)] = section_day_subject_theory.get((day, sid), 0) + length

    for session in sessions:
        hours_left = int(session["hours"])
        attempts = 0
        selected_same_day = None

        while hours_left > 0 and attempts < 1800:
            attempts += 1

            if session["session_type"] == "Lab":
                length = min(int(session["continuous_hours"]), hours_left, 4)
            elif session["continuous_required"]:
                length = min(int(session["continuous_hours"]), hours_left, 3)
            else:
                length = 1

            possible_starts = [p for p, _ in PERIODS if p + length - 1 <= 8]
            random.shuffle(possible_starts)

            pref = faculty_preferences.get(int(session["faculty_id"]), {})
            preferred_period = pref.get("preferred_period")
            if preferred_period in possible_starts:
                possible_starts.remove(preferred_period)
                possible_starts.insert(0, preferred_period)

            if selected_same_day:
                candidate_days = [selected_same_day]
            else:
                candidate_days = days[:]
                random.shuffle(candidate_days)
                preferred_day = pref.get("preferred_day")
                if preferred_day in candidate_days:
                    candidate_days.remove(preferred_day)
                    candidate_days.insert(0, preferred_day)

            placed = False
            for day in candidate_days:
                for start in possible_starts:
                    if can_place(day, start, length, session):
                        place(day, start, length, session)
                        if int(session.get("same_day_required") or 0) and session["session_type"] == "Theory":
                            selected_same_day = day
                        hours_left -= length
                        placed = True
                        break
                if placed:
                    break

            if not placed and attempts > 1500:
                return False, (
                    f"Unable to place {session['subject_name']} ({session['session_type']}). "
                    "Check rules: faculty max theory/day=3, lab/day=1, lab max=4, "
                    "if lab exists theory max=2, no same subject theory+lab on same day, "
                    "and faculty unavailable constraints."
                )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for day in days:
        for period, timing in PERIODS:
            item = grid.get((day, period))
            if item:
                rows.append((
                    section_id, day, period, timing,
                    item["subject_id"], item["faculty_id"], clean_int(item.get("room_id")),
                    item["session_type"], item.get("block_label", ""), "", generated_at, "Auto"
                ))

    execute_many("""
        INSERT INTO timetable(section_id, day, period, timing, subject_id, faculty_id, room_id, session_type, block_label, batch_label, generated_at, entry_mode)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    return True, f"Timetable generated successfully with advanced faculty/day/lab constraints. Total allocated periods: {len(rows)}"


def timetable_detail(section_id=None, faculty_id=None, room_id=None):
    query = """
        SELECT t.id, sec.year, sec.department, sec.semester, sec.section,
               t.day, t.period, t.timing,
               COALESCE(s.subject_code,'') AS subject_code,
               s.subject_name, t.session_type, t.block_label,
               f.name AS faculty, COALESCE(r.room_name,'') AS room,
               t.entry_mode, t.generated_at
        FROM timetable t
        JOIN sections sec ON t.section_id=sec.id
        JOIN subjects s ON t.subject_id=s.id
        JOIN faculty f ON t.faculty_id=f.id
        LEFT JOIN rooms r ON t.room_id=r.id
        WHERE 1=1
    """
    params = []
    if section_id:
        query += " AND t.section_id=?"
        params.append(section_id)
    if faculty_id:
        query += " AND t.faculty_id=?"
        params.append(faculty_id)
    if room_id:
        query += " AND t.room_id=?"
        params.append(room_id)

    query += """
        ORDER BY CASE t.day
            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END, t.period
    """
    return query_df(query, tuple(params))


def make_pivot(df):
    if df.empty:
        return pd.DataFrame()
    data = df.copy()
    data["entry"] = data.apply(
        lambda x: f"{x['subject_code']}\n{x['subject_name']}\n{x['session_type']} {x['block_label']}\n{x['faculty']}\n{x['room']}",
        axis=1
    )
    pivot = data.pivot_table(index="day", columns="period", values="entry", aggfunc=lambda x: "\n---\n".join(x))
    pivot = pivot.reindex(DAYS)
    for p, _ in PERIODS:
        if p not in pivot.columns:
            pivot[p] = ""
    pivot = pivot[[p for p, _ in PERIODS]]
    pivot.columns = [f"P{p}\n{PERIOD_DICT[p]}" for p, _ in PERIODS]
    return pivot.fillna("")


def export_excel(df, pivot):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pivot.to_excel(writer, sheet_name="Timetable")
        df.to_excel(writer, sheet_name="Detailed", index=False)
    return output.getvalue()

def compute_clash_counts():
    faculty = query_df("""
        SELECT day, period, faculty_id, COUNT(*) AS c FROM timetable
        GROUP BY day, period, faculty_id HAVING c > 1
    """)
    room = query_df("""
        SELECT day, period, room_id, COUNT(*) AS c FROM timetable
        WHERE room_id IS NOT NULL
        GROUP BY day, period, room_id HAVING c > 1
    """)
    section = query_df("""
        SELECT day, period, section_id, COUNT(*) AS c FROM timetable
        GROUP BY day, period, section_id HAVING c > 1
    """)
    return len(faculty), len(room), len(section)


def styled_timetable(df):
    if df.empty:
        return df

    def color_row(row):
        session = str(row.get("session_type", "")).lower()
        mode = str(row.get("entry_mode", "")).lower()
        if mode == "manual":
            return ["background-color:#fff8e1;color:#7a5800"] * len(row)
        if session == "lab":
            return ["background-color:#e8f5e9;color:#1b5e20"] * len(row)
        if session == "practical":
            return ["background-color:#fff3e0;color:#e65100"] * len(row)
        return ["background-color:#e3f2fd;color:#0d47a1"] * len(row)

    return df.style.apply(color_row, axis=1)


def create_pdf(title, df, pivot):
    if not REPORTLAB_AVAILABLE:
        content = title + "\n\n" + pivot.to_string() + "\n\nDetailed\n" + df.to_string(index=False)
        return content.encode("utf-8")

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    pdf_df = pivot.copy().reset_index()
    pdf_df = pdf_df.fillna("")
    data = [pdf_df.columns.tolist()] + pdf_df.astype(str).values.tolist()

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1b5e20")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#d4af37")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    elements.append(table)
    doc.build(elements)
    return output.getvalue()


def analytics_data():
    workload = query_df("""
        SELECT f.name, COUNT(t.id) AS assigned_hours
        FROM faculty f
        LEFT JOIN timetable t ON f.id=t.faculty_id
        GROUP BY f.id
        ORDER BY assigned_hours DESC
    """)
    room_util = query_df("""
        SELECT COALESCE(r.room_name,'No Room') AS room, COUNT(t.id) AS used_periods
        FROM rooms r
        LEFT JOIN timetable t ON r.id=t.room_id
        WHERE r.room_type IN ('Classroom','Smart Classroom','Seminar Hall','Other')
        GROUP BY r.id
        ORDER BY used_periods DESC
    """)
    lab_util = query_df("""
        SELECT COALESCE(r.room_name,'No Lab') AS lab, COUNT(t.id) AS used_periods
        FROM rooms r
        LEFT JOIN timetable t ON r.id=t.room_id
        WHERE r.room_type='Lab'
        GROUP BY r.id
        ORDER BY used_periods DESC
    """)
    return workload, room_util, lab_util


def sidebar_menu():
    role = st.session_state.get("role", "Admin")
    dept = st.session_state.get("department", "CSE")

    admin_menu = [
        "Dashboard",
        "Department Management",
        "Academic Year",
        "Faculty",
        "Sections",
        "Infrastructure",
        "Subjects & Constraints",
        "Generate Timetable",
        "Auto Clash Resolver",
        "Manual Entry",
        "Delete / Reset",
        "View / Export",
        "Clash Intelligence",
        "Faculty Workload",
        "Faculty Unavailable",
        "Faculty Preferences",
        "Approval Workflow",
        "Student Portal",
        "Faculty Swap Requests",
        "Leave Management",
        "Leave Alteration",
        "Attendance",
        "Exam Timetable",
        "Audit Log",
        "Excel Import",
        "Supabase Test",
        "Edit Records",
        "User Management",
        "Settings"
    ]

    coordinator_menu = [
        "Dashboard",
        "Faculty",
        "Sections",
        "Infrastructure",
        "Subjects & Constraints",
        "Generate Timetable",
        "Auto Clash Resolver",
        "View / Export",
        "Clash Intelligence",
        "Faculty Workload",
        "Faculty Unavailable",
        "Faculty Preferences",
        "Approval Workflow"
    ]

    hod_menu = [
        "Dashboard",
        "View / Export",
        "Clash Intelligence",
        "Faculty Workload",
        "Approval Workflow",
        "Leave Management",
        "Leave Alteration",
        "Exam Timetable",
        "Audit Log"
    ]

    principal_menu = [
        "Dashboard",
        "Approval Workflow",
        "View / Export",
        "Faculty Workload",
        "Leave Management",
        "Leave Alteration",
        "Exam Timetable",
        "Audit Log"
    ]

    faculty_menu = [
        "Dashboard",
        "View / Export",
        "Faculty Unavailable",
        "Faculty Preferences",
        "Faculty Swap Requests",
        "Leave Management",
        "Attendance"
    ]

    student_menu = [
        "Student Portal",
        "View / Export"
    ]

    if role == "Admin":
        menu = admin_menu
    elif role == "Coordinator":
        menu = coordinator_menu
    elif role == "HOD":
        menu = hod_menu
    elif role == "Principal":
        menu = principal_menu
    elif role == "Faculty":
        menu = faculty_menu
    else:
        menu = student_menu

    with st.sidebar:
        st.title("🏫 SRIT ERP")
        st.caption(f"Role: {role}")
        st.caption(f"Department: {dept}")

        page = st.radio("Menu", menu)

        if st.button("Logout", use_container_width=True):
            log_action(
                "Logout",
                f"{st.session_state.get('username','user')} logged out"
            )
            st.session_state.logged_in = False
            st.session_state.role = ""
            st.session_state.username = ""
            st.session_state.department = ""
            st.rerun()

    return page

def dashboard_page():
    header()

    role = current_role()
    dept = current_department()

    title = "Principal Executive Dashboard" if role in ["Principal", "Admin"] else f"{dept} Department Dashboard"

    st.markdown(f"""
    <div style="
        background:#ffffff;
        padding:20px;
        border-radius:16px;
        border-left:8px solid #1b5e20;
        border-right:3px solid #d4af37;
        margin-bottom:22px;
        box-shadow:0px 4px 14px rgba(0,0,0,0.12);
        text-align:center;
    ">
        <h2 style="color:#1b5e20; margin:0;">
            🏫 SRIT Academic Resource Management System (SARMS)
        </h2>
        <h4 style="color:#333333; margin-top:8px;">
            {title}
        </h4>
        <p style="font-size:17px; color:#555;">
            Department Timetable Status • Approval Monitoring • Faculty Workload • Resource Utilization
        </p>
    </div>
    """, unsafe_allow_html=True)

    if role in ["Principal", "Admin"]:
        total_departments = len(query_df("SELECT id FROM departments"))
        total_faculty = len(query_df("SELECT id FROM faculty"))
        total_sections = len(query_df("SELECT id FROM sections"))
        total_subjects = len(query_df("SELECT id FROM subjects"))
        total_classrooms = len(query_df("SELECT id FROM rooms WHERE room_type='Classroom'"))
        total_labs = len(query_df("SELECT id FROM rooms WHERE room_type='Lab'"))
        total_entries = len(query_df("SELECT id FROM timetable"))
        pending_approvals = len(query_df("""
            SELECT id FROM timetable_approvals
            WHERE status NOT IN ('Published','Approved by Principal')
        """))
        published_timetables = len(query_df("SELECT id FROM sections WHERE is_published=1"))
        leave_pending = len(query_df("SELECT id FROM faculty_leave WHERE status='Pending'"))
        exam_count = len(query_df("SELECT id FROM exam_timetable"))
        active_years = len(query_df("SELECT id FROM academic_years WHERE is_active=1"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏢 Departments", total_departments)
        c2.metric("👨‍🏫 Faculty", total_faculty)
        c3.metric("🏫 Sections", total_sections)
        c4.metric("📚 Subjects", total_subjects)

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🚪 Classrooms", total_classrooms)
        c6.metric("🖥 Labs", total_labs)
        c7.metric("⏳ Pending Approvals", pending_approvals)
        c8.metric("✅ Published", published_timetables)

        n1, n2, n3, n4 = st.columns(4)
        n1.metric("📅 Timetable Entries", total_entries)
        n2.metric("📝 Leave Pending", leave_pending)
        n3.metric("🧾 Exam Schedules", exam_count)
        n4.metric("📌 Active Academic Year", active_years)

        st.divider()
        st.subheader("🏢 Department Timetable Status")

        dept_status = query_df("""
            SELECT
                d.department_name AS Department,
                COALESCE(COUNT(sec.id), 0) AS Sections,
                COALESCE(SUM(CASE WHEN sec.is_published=1 THEN 1 ELSE 0 END), 0) AS Published,
                COALESCE(SUM(CASE WHEN ta.status IS NULL THEN 1 ELSE 0 END), 0) AS Draft,
                COALESCE(SUM(CASE WHEN ta.status='Approved by HOD' THEN 1 ELSE 0 END), 0) AS HOD_Approved,
                COALESCE(SUM(CASE WHEN ta.status='Rejected' THEN 1 ELSE 0 END), 0) AS Returned
            FROM departments d
            LEFT JOIN sections sec ON d.department_name = sec.department
            LEFT JOIN timetable_approvals ta ON sec.id = ta.section_id
            GROUP BY d.department_name
            ORDER BY d.department_name
        """)
        st.dataframe(dept_status, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("⏳ Pending Timetable Approvals")
        pending_df = query_df("""
            SELECT
                sec.department,
                sec.year,
                sec.semester,
                sec.section,
                COALESCE(ta.status, 'Draft') AS status,
                COALESCE(ta.hod_comment, '') AS hod_comment,
                COALESCE(ta.principal_comment, '') AS principal_comment,
                COALESCE(ta.updated_at, '') AS updated_at
            FROM sections sec
            LEFT JOIN timetable_approvals ta ON sec.id = ta.section_id
            WHERE COALESCE(ta.status, 'Draft') NOT IN ('Published','Approved by Principal')
            ORDER BY sec.department, sec.year, sec.semester, sec.section
        """)
        if not pending_df.empty:
            st.dataframe(pending_df, use_container_width=True, hide_index=True)
        else:
            st.success("No pending timetable approvals.")

        st.divider()
        st.subheader("🔔 Executive Notifications")
        faculty_clashes, room_clashes, section_clashes = compute_clash_counts()
        total_clashes = faculty_clashes + room_clashes + section_clashes
        noti1, noti2, noti3 = st.columns(3)

        with noti1:
            if pending_approvals > 0:
                st.warning(f"{pending_approvals} timetable approval(s) pending.")
            else:
                st.success("All timetables cleared.")

        with noti2:
            if leave_pending > 0:
                st.warning(f"{leave_pending} leave request(s) pending.")
            else:
                st.success("No pending leave request.")

        with noti3:
            if total_clashes > 0:
                st.error(f"{total_clashes} clash(es) detected.")
            else:
                st.success("No timetable clashes detected.")

        st.divider()
        st.subheader("📊 Institution Analytics")
        workload = query_df("""
            SELECT f.department, f.name, COUNT(t.id) AS assigned_hours
            FROM faculty f
            LEFT JOIN timetable t ON f.id=t.faculty_id
            GROUP BY f.id
            ORDER BY f.department, assigned_hours DESC
        """)
        room_util = query_df("""
            SELECT COALESCE(r.department,'') AS department,
                   COALESCE(r.room_name,'No Room') AS room,
                   COUNT(t.id) AS used_periods
            FROM rooms r
            LEFT JOIN timetable t ON r.id=t.room_id
            GROUP BY r.id
            ORDER BY department, used_periods DESC
        """)
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("#### Faculty Workload")
            if not workload.empty:
                chart_df = workload.copy()
                chart_df["faculty"] = chart_df["department"].astype(str) + " - " + chart_df["name"].astype(str)
                st.bar_chart(chart_df.set_index("faculty")["assigned_hours"])
            else:
                st.info("No faculty workload data yet.")
        with a2:
            st.markdown("#### Room / Lab Utilization")
            if not room_util.empty:
                chart_df = room_util.copy()
                chart_df["room_label"] = chart_df["department"].astype(str) + " - " + chart_df["room"].astype(str)
                st.bar_chart(chart_df.set_index("room_label")["used_periods"])
            else:
                st.info("No room utilization data yet.")

        st.divider()
        st.subheader("🕘 Recent Activities")
        recent = query_df("""
            SELECT action, details, username, created_at
            FROM audit_log
            ORDER BY id DESC
            LIMIT 10
        """)
        if not recent.empty:
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity recorded.")

    else:
        st.subheader(f"🏢 {dept} Department Dashboard")
        faculty_count = len(query_df("SELECT id FROM faculty WHERE department=?", (dept,)))
        section_count = len(query_df("SELECT id FROM sections WHERE department=?", (dept,)))
        classroom_count = len(query_df("SELECT id FROM rooms WHERE department=? AND room_type='Classroom'", (dept,)))
        lab_count = len(query_df("SELECT id FROM rooms WHERE department=? AND room_type='Lab'", (dept,)))
        subject_count = len(query_df("""
            SELECT s.id
            FROM subjects s
            JOIN sections sec ON s.section_id=sec.id
            WHERE sec.department=?
        """, (dept,)))
        entry_count = len(query_df("""
            SELECT t.id
            FROM timetable t
            JOIN sections sec ON t.section_id=sec.id
            WHERE sec.department=?
        """, (dept,)))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👨‍🏫 Faculty", faculty_count)
        c2.metric("🏫 Sections", section_count)
        c3.metric("📚 Subjects", subject_count)
        c4.metric("📅 Entries", entry_count)

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🚪 Classrooms", classroom_count)
        c6.metric("🖥 Labs", lab_count)
        c7.metric("🏢 Department", dept)
        c8.metric("👤 Role", role)

        st.divider()
        st.subheader("📊 Department Faculty Workload")
        workload = query_df("""
            SELECT f.name, COUNT(t.id) AS assigned_hours
            FROM faculty f
            LEFT JOIN timetable t ON f.id=t.faculty_id
            WHERE f.department=?
            GROUP BY f.id
            ORDER BY assigned_hours DESC
        """, (dept,))
        if not workload.empty:
            st.bar_chart(workload.set_index("name")["assigned_hours"])
        else:
            st.info("No timetable generated yet for this department.")

    st.subheader("⏱ SRIT Academic Time Grid")
    time_grid = pd.DataFrame(PERIODS, columns=["PERIOD", "TIMING"])
    st.table(time_grid)

def faculty_page():
    header()
    st.subheader("Faculty Management")

    with st.form("faculty_form"):
        c1, c2, c3, c4 = st.columns(4)

        name = c1.text_input("Faculty Name")
        designation = c2.text_input("Designation", "AP/CSE")

        if can_view_all_departments():
            department = c3.text_input("Department", "CSE")
        else:
            department = current_department()
            c3.text_input("Department", department, disabled=True)

        max_hours = c4.number_input("Max Hours / Week", 1, 40, 24)

        if st.form_submit_button("Save Faculty", use_container_width=True) and name:
            try:
                execute(
                    "INSERT INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)",
                    (name, designation, department, max_hours)
                )
                st.success("Faculty saved.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Faculty already exists.")

    if can_view_all_departments():
        faculty_data = query_df("SELECT * FROM faculty ORDER BY department, name")
    else:
        faculty_data = query_df(
            "SELECT * FROM faculty WHERE department=? ORDER BY name",
            (current_department(),)
        )

    st.dataframe(faculty_data, use_container_width=True, hide_index=True)

def sections_page():
    header()
    st.subheader("Class / Section Management")

    with st.form("section_form"):
        c1, c2, c3, c4, c5 = st.columns(5)

        year = c1.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        semester = c2.selectbox("Semester", ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"])

        if can_view_all_departments():
            department = c3.text_input("Department", "CSE")
        else:
            department = current_department()
            c3.text_input("Department", department, disabled=True)

        section = c4.text_input("Section", "A")
        working_days = c5.selectbox("Working Days", [5, 6], index=1)

        if st.form_submit_button("Save Class / Section", use_container_width=True):
            try:
                execute(
                    "INSERT INTO sections(year, department, semester, section, working_days) VALUES(?,?,?,?,?)",
                    (year, department, semester, section, working_days)
                )
                st.success("Section saved.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Section already exists.")

    if can_view_all_departments():
        section_data = query_df("SELECT * FROM sections ORDER BY year, department, semester, section")
    else:
        section_data = query_df(
            "SELECT * FROM sections WHERE department=? ORDER BY year, semester, section",
            (current_department(),)
        )

    st.dataframe(section_data, use_container_width=True, hide_index=True)

def rooms_page():
    header()
    st.subheader("Infrastructure Management")

    with st.form("room_form"):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1.5, 1])

        room_name = c1.text_input("Room / Lab Name")
        room_type = c2.selectbox("Type", ["Classroom", "Lab", "Seminar Hall", "Smart Classroom", "Other"])
        capacity = c3.number_input("Capacity", 1, 300, 60)
        equipment = c4.text_input("Equipment", "Projector")

        if can_view_all_departments():
            department = c5.text_input("Department", "CSE")
        else:
            department = current_department()
            c5.text_input("Department", department, disabled=True)

        if st.form_submit_button("Save Infrastructure", use_container_width=True) and room_name:
            try:
                execute(
                    "INSERT INTO rooms(room_name, room_type, capacity, equipment, department) VALUES(?,?,?,?,?)",
                    (room_name, room_type, capacity, equipment, department)
                )
                st.success("Infrastructure saved.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Room / Lab already exists.")

    if can_view_all_departments():
        room_data = query_df("SELECT * FROM rooms ORDER BY department, room_type, room_name")
    else:
        room_data = query_df(
            "SELECT * FROM rooms WHERE department=? ORDER BY room_type, room_name",
            (current_department(),)
        )

    st.dataframe(room_data, use_container_width=True, hide_index=True)

def subjects_page():
    header()
    st.subheader("Subjects & Constraint Mapping")

    fdf = faculty_df()
    sdf = section_label_df()
    rdf = rooms_df()

    if can_view_all_departments():
        lab_rdf = query_df("SELECT id, room_name FROM rooms WHERE room_type='Lab' ORDER BY department, room_name")
        class_rdf = query_df("""
            SELECT id, room_name
            FROM rooms
            WHERE room_type IN ('Classroom','Smart Classroom')
            ORDER BY department, room_name
        """)
    else:
        lab_rdf = query_df(
            "SELECT id, room_name FROM rooms WHERE room_type='Lab' AND department=? ORDER BY room_name",
            (current_department(),)
        )
        class_rdf = query_df("""
            SELECT id, room_name
            FROM rooms
            WHERE room_type IN ('Classroom','Smart Classroom') AND department=?
            ORDER BY room_name
        """, (current_department(),))

    if fdf.empty or sdf.empty:
        st.warning("Add faculty and sections first.")
        return

    subject_type = st.selectbox(
        "Subject Type",
        ["Theory", "Lab", "Theory + Lab", "Practical"],
        key="subject_type_selector"
    )

    with st.form("subject_form"):
        code = st.text_input("Subject Code")
        subject_name = st.text_input("Subject Name")

        section_name = st.selectbox("Which Class / Section?", sdf["label"].tolist())
        section_id = int(sdf[sdf["label"] == section_name]["id"].iloc[0])

        same_day_theory = False
        theory_hours = 0
        lab_hours = 0
        weekly_hours = 0
        theory_cont = False
        theory_cont_hours = 1
        lab_cont = False
        lab_cont_hours = 1

        st.markdown("### Hours & Continuous Period Constraints")

        if subject_type == "Theory":
            theory_hours = st.number_input("Theory Hours / Week", 1, 10, 3)
            weekly_hours = theory_hours
            same_day_theory = st.checkbox("Schedule All Theory Hours On Same Day?")
            theory_cont = st.checkbox("Theory Continuous Period Required?")
            if theory_cont:
                theory_cont_hours = st.number_input("How many continuous theory periods?", 2, 8, 2)

        elif subject_type in ["Lab", "Practical"]:
            lab_hours = st.number_input("Lab Hours / Week", 1, 10, 4)
            weekly_hours = lab_hours
            st.info("Lab continuous period is mandatory.")
            lab_cont = True
            lab_cont_hours = st.number_input("How many continuous lab periods?", 1, 8, lab_hours)

        elif subject_type == "Theory + Lab":
            c1, c2 = st.columns(2)
            theory_hours = c1.number_input("Theory Hours / Week", 1, 10, 2)
            lab_hours = c2.number_input("Lab Hours / Week", 1, 10, 2)
            weekly_hours = theory_hours + lab_hours
            same_day_theory = st.checkbox("Schedule All Theory Hours On Same Day?")
            theory_cont = st.checkbox("Theory Continuous Period Required?")
            if theory_cont:
                theory_cont_hours = st.number_input("How many continuous theory periods?", 2, 8, 2)
            st.info("Lab continuous period is mandatory for Theory + Lab.")
            lab_cont = True
            lab_cont_hours = st.number_input("How many continuous lab periods?", 1, 8, lab_hours)

        st.markdown("### Faculty and Room / Lab Mapping")

        faculty_name = st.selectbox("Theory / Main Faculty", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

        lab_faculty_id = None
        if subject_type in ["Lab", "Theory + Lab", "Practical"]:
            lab_faculty_name = st.selectbox("Lab Faculty", fdf["name"].tolist())
            lab_faculty_id = int(fdf[fdf["name"] == lab_faculty_name]["id"].iloc[0])

        room_options = ["None"] + (class_rdf["room_name"].tolist() if not class_rdf.empty else rdf["room_name"].tolist())
        room_name = st.selectbox("Which Classroom?", room_options)

        room_id = None
        if room_name != "None":
            all_rooms = rooms_df()
            room_id = int(all_rooms[all_rooms["room_name"] == room_name]["id"].iloc[0])

        lab_room_id = None
        if subject_type in ["Lab", "Theory + Lab", "Practical"]:
            lab_options = ["None"] + (lab_rdf["room_name"].tolist() if not lab_rdf.empty else rdf["room_name"].tolist())
            lab_room_name = st.selectbox("Which Lab?", lab_options)
            if lab_room_name != "None":
                all_rooms = rooms_df()
                lab_room_id = int(all_rooms[all_rooms["room_name"] == lab_room_name]["id"].iloc[0])

        if st.form_submit_button("Save Subject Constraint", use_container_width=True) and subject_name:
            execute("""
                INSERT INTO subjects(
                    subject_code, subject_name, subject_type, weekly_hours,
                    theory_hours, lab_hours,
                    theory_continuous_required, theory_continuous_hours,
                    same_day_theory,
                    lab_continuous_required, lab_continuous_hours,
                    faculty_id, lab_faculty_id, section_id, room_id, lab_room_id
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                code, subject_name, subject_type, weekly_hours,
                theory_hours, lab_hours,
                1 if theory_cont else 0,
                int(theory_cont_hours),
                1 if same_day_theory else 0,
                1 if lab_cont else 0,
                int(lab_cont_hours),
                faculty_id, lab_faculty_id, section_id, room_id, lab_room_id
            ))
            st.success("Subject and constraints saved.")
            st.rerun()

    if can_view_all_departments():
        df = query_df("""
            SELECT s.id, s.subject_code, s.subject_name, s.subject_type,
                   s.weekly_hours, s.theory_hours, s.lab_hours,
                   s.theory_continuous_required, s.theory_continuous_hours,
                   s.same_day_theory,
                   s.lab_continuous_required, s.lab_continuous_hours,
                   f.name AS theory_faculty,
                   lf.name AS lab_faculty,
                   sec.year, sec.department, sec.semester, sec.section,
                   r.room_name AS classroom,
                   lr.room_name AS lab
            FROM subjects s
            JOIN faculty f ON s.faculty_id=f.id
            LEFT JOIN faculty lf ON s.lab_faculty_id=lf.id
            JOIN sections sec ON s.section_id=sec.id
            LEFT JOIN rooms r ON s.room_id=r.id
            LEFT JOIN rooms lr ON s.lab_room_id=lr.id
            ORDER BY sec.department, sec.year, sec.semester, sec.section, s.subject_name
        """)
    else:
        df = query_df("""
            SELECT s.id, s.subject_code, s.subject_name, s.subject_type,
                   s.weekly_hours, s.theory_hours, s.lab_hours,
                   s.theory_continuous_required, s.theory_continuous_hours,
                   s.same_day_theory,
                   s.lab_continuous_required, s.lab_continuous_hours,
                   f.name AS theory_faculty,
                   lf.name AS lab_faculty,
                   sec.year, sec.department, sec.semester, sec.section,
                   r.room_name AS classroom,
                   lr.room_name AS lab
            FROM subjects s
            JOIN faculty f ON s.faculty_id=f.id
            LEFT JOIN faculty lf ON s.lab_faculty_id=lf.id
            JOIN sections sec ON s.section_id=sec.id
            LEFT JOIN rooms r ON s.room_id=r.id
            LEFT JOIN rooms lr ON s.lab_room_id=lr.id
            WHERE sec.department=?
            ORDER BY sec.year, sec.semester, sec.section, s.subject_name
        """, (current_department(),))

    st.dataframe(df, use_container_width=True, hide_index=True)

def manual_entry_page():
    header()
    st.subheader("Manual Timetable Entry")

    sdf = section_label_df()
    fdf = faculty_df()
    rdf = rooms_df()

    if sdf.empty or fdf.empty:
        st.warning("Add section and faculty first.")
        return

    section_name = st.selectbox("Select Class / Section", sdf["label"].tolist())
    section_id = int(sdf[sdf["label"] == section_name]["id"].iloc[0])
    subdf = subject_label_df(section_id)

    if subdf.empty:
        st.warning("Add subjects for this section first.")
        return

    with st.form("manual_entry"):
        c1, c2, c3 = st.columns(3)
        day = c1.selectbox("Day", DAYS)
        start_period = c2.selectbox("Start Period", [p for p, _ in PERIODS])
        continuous_periods = c3.number_input("How many continuous periods?", 1, 8, 1)

        subject_label = st.selectbox("Subject", subdf["label"].tolist())
        subject_id = int(subdf[subdf["label"] == subject_label]["id"].iloc[0])

        faculty_name = st.selectbox("Faculty", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

        room_name = st.selectbox("Room / Lab", ["None"] + rdf["room_name"].tolist())
        room_id = None if room_name == "None" else int(rdf[rdf["room_name"] == room_name]["id"].iloc[0])

        session_type = st.selectbox("Session Type", ["Theory", "Lab", "Practical", "Other"])
        force_save = st.checkbox("Force save even if clash exists?")

        submitted = st.form_submit_button("Save Manual Entry", use_container_width=True)

    if submitted:
        conflict_msgs = []
        for p in range(int(start_period), int(start_period) + int(continuous_periods)):
            if p not in PERIOD_DICT:
                conflict_msgs.append(f"Invalid period P{p}.")
                continue

            clash = query_df("""
                SELECT id FROM timetable
                WHERE day=? AND period=?
                AND (
                    section_id=?
                    OR faculty_id=?
                    OR (? IS NOT NULL AND room_id=?)
                )
            """, (day, p, section_id, faculty_id, room_id, room_id))

            if not clash.empty:
                conflict_msgs.append(f"Clash found on {day} P{p}.")

        if conflict_msgs and not force_save:
            st.error("Cannot save due to clash: " + " ".join(conflict_msgs))
        else:
            generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows = []
            for p in range(int(start_period), int(start_period) + int(continuous_periods)):
                if p in PERIOD_DICT:
                    rows.append((section_id, day, p, PERIOD_DICT[p], subject_id, faculty_id, room_id, session_type, f"Manual-{continuous_periods}P", "", generated_at, "Manual"))
            execute_many("""
                INSERT INTO timetable(section_id, day, period, timing, subject_id, faculty_id, room_id, session_type, block_label, batch_label, generated_at, entry_mode)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """, rows)
            st.success("Manual timetable entry saved.")

    st.dataframe(timetable_detail(section_id=section_id), use_container_width=True, hide_index=True)


def generate_page():
    header()
    st.subheader("Automatic Timetable Generator")

    sdf = section_label_df()
    if sdf.empty:
        st.warning("Add sections first.")
        return

    section_name = st.selectbox("Select Class / Section", sdf["label"].tolist())
    selected = sdf[sdf["label"] == section_name].iloc[0]
    section_id = int(selected["id"])
    working_days = int(selected["working_days"])

    clear_old = st.checkbox(
        "Clear old timetable for this section before generating",
        value=True
    )

    col1, col2 = st.columns(2)

    with col1:
        generate_btn = st.button(
            "Generate Clash-Free Timetable",
            type="primary",
            use_container_width=True
        )

    with col2:
        regenerate_btn = st.button(
            "Regenerate Optimized Timetable",
            use_container_width=True
        )

    if generate_btn:
        ok, msg = generate_for_section(
            section_id,
            working_days,
            clear_old=clear_old
        )

        if ok:
            st.success(msg)
            df = timetable_detail(section_id=section_id)
            st.dataframe(make_pivot(df), use_container_width=True)
        else:
            st.error(msg)

    if regenerate_btn:
        ok, msg = generate_for_section(
            section_id,
            working_days,
            clear_old=True
        )

        if ok:
            st.success("Timetable regenerated successfully.")
            df = timetable_detail(section_id=section_id)
            st.dataframe(make_pivot(df), use_container_width=True)
        else:
            st.error(msg)


def delete_reset_page():
    header()
    st.subheader("Delete / Edit / Reset Timetable Entries")

    tab1, tab2, tab3 = st.tabs(["Delete Single Entry", "Edit Entry", "Clear Timetable"])

    with tab1:
        df = timetable_detail()
        if df.empty:
            st.info("No timetable entries found.")
        else:
            df["display"] = df.apply(lambda x: f"ID {x['id']} | {x['day']} P{x['period']} | {x['subject_name']} | {x['faculty']} | {x['room']}", axis=1)
            selected = st.selectbox("Select wrong entry to delete", df["display"].tolist(), key="delete_entry_select")
            selected_id = int(selected.split("|")[0].replace("ID", "").strip())
            if st.button("Delete Selected Entry", type="primary"):
                execute("DELETE FROM timetable WHERE id=?", (selected_id,))
                st.success("Selected timetable entry deleted.")
                st.rerun()

    with tab2:
        df = timetable_detail()
        if df.empty:
            st.info("No timetable entries available to edit.")
        else:
            df["display"] = df.apply(lambda x: f"ID {x['id']} | {x['day']} P{x['period']} | {x['subject_name']} | {x['faculty']} | {x['room']}", axis=1)
            selected = st.selectbox("Select entry to edit", df["display"].tolist(), key="edit_entry_select")
            selected_id = int(selected.split("|")[0].replace("ID", "").strip())
            current = query_df("SELECT * FROM timetable WHERE id=?", (selected_id,)).iloc[0]

            fdf = faculty_df()
            rdf = rooms_df()
            subdf = subject_label_df(int(current["section_id"]))

            with st.form("edit_entry_form"):
                c1, c2, c3 = st.columns(3)
                day = c1.selectbox("Day", DAYS, index=DAYS.index(current["day"]) if current["day"] in DAYS else 0)
                period_values = [p for p, _ in PERIODS]
                period = c2.selectbox("Period", period_values, index=period_values.index(int(current["period"])))
                session_type = c3.selectbox("Session Type", ["Theory", "Lab", "Practical", "Other"], index=["Theory", "Lab", "Practical", "Other"].index(current["session_type"]) if current["session_type"] in ["Theory", "Lab", "Practical", "Other"] else 0)

                subject_label = st.selectbox("Subject", subdf["label"].tolist())
                subject_id = int(subdf[subdf["label"] == subject_label]["id"].iloc[0])

                faculty_name = st.selectbox("Faculty", fdf["name"].tolist())
                faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

                room_name = st.selectbox("Room / Lab", ["None"] + rdf["room_name"].tolist())
                room_id = None if room_name == "None" else int(rdf[rdf["room_name"] == room_name]["id"].iloc[0])

                if st.form_submit_button("Update Entry", use_container_width=True):
                    execute("""
                        UPDATE timetable
                        SET day=?, period=?, timing=?, subject_id=?, faculty_id=?, room_id=?, session_type=?, entry_mode='Manual'
                        WHERE id=?
                    """, (day, period, PERIOD_DICT[int(period)], subject_id, faculty_id, room_id, session_type, selected_id))
                    st.success("Timetable entry updated.")
                    st.rerun()

    with tab3:
        sdf = section_label_df()
        if not sdf.empty:
            section_name = st.selectbox("Clear timetable for class", sdf["label"].tolist(), key="clear_section_select")
            section_id = int(sdf[sdf["label"] == section_name]["id"].iloc[0])
            if st.button("Clear Selected Class Timetable"):
                execute("DELETE FROM timetable WHERE section_id=?", (section_id,))
                st.success("Selected class timetable cleared.")
        if st.button("Clear Complete Timetable"):
            execute("DELETE FROM timetable")
            st.warning("Complete timetable cleared.")


def view_export_page():
    header()
    st.subheader("View / Export Timetable")

    mode = st.radio("View Mode", ["Class Timetable", "Faculty Timetable", "Room / Lab Timetable"], horizontal=True)

    search_text = st.text_input("🔎 Search / Filter by subject, faculty, room, day, section", key="global_search_filter")

    df = pd.DataFrame()
    title = "Timetable"

    if mode == "Class Timetable":
        sdf = section_label_df()
        if sdf.empty:
            st.warning("No section available.")
            return
        label = st.selectbox("Select Class / Section", sdf["label"].tolist())
        section_id = int(sdf[sdf["label"] == label]["id"].iloc[0])
        df = timetable_detail(section_id=section_id)
        title = label

    elif mode == "Faculty Timetable":
        fdf = faculty_df()
        if fdf.empty:
            st.warning("No faculty available.")
            return
        label = st.selectbox("Select Faculty", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == label]["id"].iloc[0])
        df = timetable_detail(faculty_id=faculty_id)
        title = label

    else:
        rdf = rooms_df()
        if rdf.empty:
            st.warning("No room/lab available.")
            return
        label = st.selectbox("Select Room / Lab", rdf["room_name"].tolist())
        room_id = int(rdf[rdf["room_name"] == label]["id"].iloc[0])
        df = timetable_detail(room_id=room_id)
        title = label

    if search_text and not df.empty:
        mask = df.astype(str).apply(lambda col: col.str.contains(search_text, case=False, na=False)).any(axis=1)
        df = df[mask]

    pivot = make_pivot(df)

    st.markdown("#### Color Guide: Theory = Blue | Lab = Green | Practical = Orange | Manual = Gold")
    st.dataframe(pivot, use_container_width=True)

    st.markdown("#### Detailed Entries")
    if not df.empty:
        st.dataframe(styled_timetable(df), use_container_width=True, hide_index=True)
    else:
        st.info("No entries found.")

    if not df.empty:
        excel = export_excel(df, pivot)
        pdf = create_pdf(f"{title} - {mode}", df, pivot)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download Excel",
                data=excel,
                file_name=f"{title.replace(' ', '_')}_Timetable.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with c2:
            st.download_button(
                "Download PDF",
                data=pdf,
                file_name=f"{title.replace(' ', '_')}_Timetable.pdf",
                mime="application/pdf" if REPORTLAB_AVAILABLE else "text/plain",
                use_container_width=True
            )


def clash_page():
    header()
    st.subheader("Clash Intelligence")

    faculty_clash = query_df("""
        SELECT day, period, faculty_id, COUNT(*) AS clash_count
        FROM timetable
        GROUP BY day, period, faculty_id
        HAVING clash_count > 1
    """)

    room_clash = query_df("""
        SELECT day, period, room_id, COUNT(*) AS clash_count
        FROM timetable
        WHERE room_id IS NOT NULL
        GROUP BY day, period, room_id
        HAVING clash_count > 1
    """)

    section_clash = query_df("""
        SELECT day, period, section_id, COUNT(*) AS clash_count
        FROM timetable
        GROUP BY day, period, section_id
        HAVING clash_count > 1
    """)

    if faculty_clash.empty and room_clash.empty and section_clash.empty:
        st.success("No faculty, room/lab, or class clashes found.")
    else:
        st.error("Clashes detected.")
        st.write("Faculty Clash")
        st.dataframe(faculty_clash, use_container_width=True)
        st.write("Room / Lab Clash")
        st.dataframe(room_clash, use_container_width=True)
        st.write("Class / Section Clash")
        st.dataframe(section_clash, use_container_width=True)


def workload_page():
    header()
    st.subheader("Faculty Workload")

    workload = query_df("""
        SELECT f.name, f.designation, f.department, f.max_hours,
               COUNT(t.id) AS assigned_hours,
               f.max_hours - COUNT(t.id) AS remaining_hours
        FROM faculty f
        LEFT JOIN timetable t ON f.id=t.faculty_id
        GROUP BY f.id
        ORDER BY f.name
    """)

    st.dataframe(workload, use_container_width=True, hide_index=True)
    
def edit_records_page():
    header()
    st.subheader("Edit Records")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Edit Faculty",
        "Edit Subject",
        "Edit Section",
        "Edit Infrastructure",
        "Edit Timetable Entry"
    ])

    with tab1:
        df = query_df("SELECT * FROM faculty ORDER BY name")
        if df.empty:
            st.info("No faculty found.")
        else:
            selected = st.selectbox("Select Faculty", df["name"].tolist(), key="edit_faculty_select")
            row = df[df["name"] == selected].iloc[0]

            name = st.text_input("Faculty Name", row["name"], key="edit_faculty_name")
            designation = st.text_input("Designation", row["designation"], key="edit_faculty_designation")
            department = st.text_input("Department", row["department"], key="edit_faculty_department")
            max_hours = st.number_input("Max Hours", 1, 40, int(row["max_hours"]), key="edit_faculty_max")

            if st.button("Update Faculty"):
                execute(
                    "UPDATE faculty SET name=?, designation=?, department=?, max_hours=? WHERE id=?",
                    (name, designation, department, max_hours, int(row["id"]))
                )
                st.success("Faculty updated.")
                st.rerun()

    with tab2:
        df = query_df("SELECT id, subject_code, subject_name, subject_type, weekly_hours, theory_hours, lab_hours FROM subjects ORDER BY subject_name")
        if df.empty:
            st.info("No subjects found.")
        else:
            search = st.text_input("Search Subject", key="search_subject_edit")
            if search:
                df = df[df["subject_name"].str.contains(search, case=False, na=False)]

            st.dataframe(df, use_container_width=True, hide_index=True)

            sid = st.number_input("Enter Subject ID to Edit", 1, 99999, key="edit_subject_id")
            rowdf = query_df("SELECT * FROM subjects WHERE id=?", (sid,))
            if not rowdf.empty:
                row = rowdf.iloc[0]

                subject_code = st.text_input("Subject Code", row["subject_code"], key="edit_sub_code")
                subject_name = st.text_input("Subject Name", row["subject_name"], key="edit_sub_name")
                subject_type = st.selectbox(
                    "Subject Type",
                    ["Theory", "Lab", "Theory + Lab", "Practical"],
                    index=["Theory", "Lab", "Theory + Lab", "Practical"].index(row["subject_type"]) if row["subject_type"] in ["Theory", "Lab", "Theory + Lab", "Practical"] else 0,
                    key="edit_sub_type"
                )
                theory_hours = st.number_input("Theory Hours", 0, 10, int(row["theory_hours"]), key="edit_theory_hours")
                lab_hours = st.number_input("Lab Hours", 0, 10, int(row["lab_hours"]), key="edit_lab_hours")
                weekly_hours = theory_hours + lab_hours if subject_type == "Theory + Lab" else int(row["weekly_hours"])

                if st.button("Update Subject"):
                    execute(
                        "UPDATE subjects SET subject_code=?, subject_name=?, subject_type=?, weekly_hours=?, theory_hours=?, lab_hours=? WHERE id=?",
                        (subject_code, subject_name, subject_type, weekly_hours, theory_hours, lab_hours, sid)
                    )
                    st.success("Subject updated.")
                    st.rerun()

    with tab3:
        df = query_df("SELECT * FROM sections ORDER BY year, department, semester, section")
        if df.empty:
            st.info("No sections found.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            section_id = st.number_input("Enter Section ID to Edit", 1, 99999, key="edit_section_id")
            rowdf = query_df("SELECT * FROM sections WHERE id=?", (section_id,))
            if not rowdf.empty:
                row = rowdf.iloc[0]

                year = st.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"], key="edit_year")
                department = st.text_input("Department", row["department"], key="edit_sec_dept")
                semester = st.text_input("Semester", row["semester"], key="edit_sec_sem")
                section = st.text_input("Section", row["section"], key="edit_sec_section")
                working_days = st.selectbox("Working Days", [5, 6], index=1, key="edit_working_days")

                if st.button("Update Section"):
                    execute(
                        "UPDATE sections SET year=?, department=?, semester=?, section=?, working_days=? WHERE id=?",
                        (year, department, semester, section, working_days, section_id)
                    )
                    st.success("Section updated.")
                    st.rerun()

    with tab4:
        df = query_df("SELECT * FROM rooms ORDER BY room_type, room_name")
        if df.empty:
            st.info("No infrastructure found.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            room_id = st.number_input("Enter Room/Lab ID to Edit", 1, 99999, key="edit_room_id")
            rowdf = query_df("SELECT * FROM rooms WHERE id=?", (room_id,))
            if not rowdf.empty:
                row = rowdf.iloc[0]

                room_name = st.text_input("Room / Lab Name", row["room_name"], key="edit_room_name")
                room_type = st.selectbox("Type", ["Classroom", "Lab", "Seminar Hall", "Smart Classroom", "Other"], key="edit_room_type")
                capacity = st.number_input("Capacity", 1, 300, int(row["capacity"]), key="edit_room_capacity")
                equipment = st.text_input("Equipment", row["equipment"], key="edit_room_equipment")

                if st.button("Update Infrastructure"):
                    execute(
                        "UPDATE rooms SET room_name=?, room_type=?, capacity=?, equipment=? WHERE id=?",
                        (room_name, room_type, capacity, equipment, room_id)
                    )
                    st.success("Infrastructure updated.")
                    st.rerun()

    with tab5:
        df = timetable_detail()
        if df.empty:
            st.info("No timetable entries found.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            timetable_id = st.number_input("Enter Timetable ID to Edit", 1, 99999, key="edit_tt_id")
            rowdf = query_df("SELECT * FROM timetable WHERE id=?", (timetable_id,))
            if not rowdf.empty:
                row = rowdf.iloc[0]

                day = st.selectbox("Day", DAYS, key="edit_tt_day")
                period = st.selectbox("Period", [p for p, _ in PERIODS], key="edit_tt_period")
                session_type = st.selectbox("Session Type", ["Theory", "Lab", "Practical", "Other"], key="edit_tt_type")

                if st.button("Update Timetable Entry"):
                    execute(
                        "UPDATE timetable SET day=?, period=?, timing=?, session_type=? WHERE id=?",
                        (day, period, PERIOD_DICT[period], session_type, timetable_id)
                    )
                    st.success("Timetable entry updated.")
                    st.rerun()


def faculty_unavailable_page():
    header()
    st.subheader("Faculty Unavailable Period Constraints")

    fdf = faculty_df()

    if fdf.empty:
        st.warning("Add faculty first.")
        return

    st.info("Use this page when a faculty member says: Do not assign me on Monday Period 1, Tuesday Period 6, Friday Period 8, etc.")

    with st.form("faculty_unavailable_form"):
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.2, 2])

        faculty_name = c1.selectbox("Faculty", fdf["name"].tolist(), key="unavailable_faculty")
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

        day = c2.selectbox("Unavailable Day", DAYS, key="unavailable_day")
        period = c3.selectbox("Unavailable Period", [p for p, _ in PERIODS], key="unavailable_period")
        reason = c4.text_input("Reason", "Faculty not available", key="unavailable_reason")

        submitted = st.form_submit_button("Save Faculty Unavailable Constraint", use_container_width=True)

        if submitted:
            try:
                execute(
                    """
                    INSERT INTO faculty_unavailable(faculty_id, day, period, reason)
                    VALUES(?,?,?,?)
                    """,
                    (faculty_id, day, period, reason)
                )
                st.success(f"Saved: {faculty_name} is unavailable on {day} Period {period}.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("This unavailable constraint already exists.")

    st.markdown("### Existing Faculty Unavailable Constraints")

    data = query_df("""
        SELECT
            fu.id,
            f.name AS faculty,
            fu.day,
            fu.period,
            fu.reason
        FROM faculty_unavailable fu
        JOIN faculty f ON fu.faculty_id = f.id
        ORDER BY
            f.name,
            CASE fu.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
            END,
            fu.period
    """)

    st.dataframe(data, use_container_width=True, hide_index=True)

    if not data.empty:
        st.markdown("### Delete Constraint")
        delete_id = st.number_input("Enter Constraint ID to Delete", min_value=1, step=1, key="delete_unavailable_constraint_id")

        if st.button("Delete Selected Constraint", use_container_width=True):
            execute("DELETE FROM faculty_unavailable WHERE id=?", (int(delete_id),))
            st.success("Faculty unavailable constraint deleted.")
            st.rerun()


def faculty_preferences_page():
    header()
    st.subheader("Faculty Preferences")

    fdf = faculty_df()

    if fdf.empty:
        st.warning("Add faculty first.")
        return

    st.info("Use this page to set preferred day, preferred period, and avoid last-period preference for each faculty.")

    with st.form("faculty_preferences_form"):
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 2])

        faculty_name = c1.selectbox("Faculty", fdf["name"].tolist(), key="pref_faculty")
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

        preferred_day = c2.selectbox("Preferred Day", ["No Preference"] + DAYS, key="pref_day")
        preferred_period = c3.selectbox("Preferred Period", ["No Preference"] + [p for p, _ in PERIODS], key="pref_period")
        avoid_last_period = c4.checkbox("Avoid Last Period?", key="pref_avoid_last")
        remarks = st.text_input("Remarks", "", key="pref_remarks")

        submitted = st.form_submit_button("Save Faculty Preference", use_container_width=True)

        if submitted:
            preferred_day_value = "" if preferred_day == "No Preference" else preferred_day
            preferred_period_value = None if preferred_period == "No Preference" else int(preferred_period)

            execute(
                """
                INSERT INTO faculty_preferences(
                    faculty_id, preferred_day, preferred_period, avoid_last_period, remarks
                )
                VALUES(?,?,?,?,?)
                ON CONFLICT(faculty_id) DO UPDATE SET
                    preferred_day=excluded.preferred_day,
                    preferred_period=excluded.preferred_period,
                    avoid_last_period=excluded.avoid_last_period,
                    remarks=excluded.remarks
                """,
                (
                    faculty_id,
                    preferred_day_value,
                    preferred_period_value,
                    1 if avoid_last_period else 0,
                    remarks
                )
            )
            st.success("Faculty preference saved.")
            st.rerun()

    st.markdown("### Existing Faculty Preferences")

    data = query_df("""
        SELECT
            fp.id,
            f.name AS faculty,
            COALESCE(fp.preferred_day, '') AS preferred_day,
            COALESCE(fp.preferred_period, '') AS preferred_period,
            CASE WHEN fp.avoid_last_period=1 THEN 'Yes' ELSE 'No' END AS avoid_last_period,
            COALESCE(fp.remarks, '') AS remarks
        FROM faculty_preferences fp
        JOIN faculty f ON fp.faculty_id = f.id
        ORDER BY f.name
    """)

    st.dataframe(data, use_container_width=True, hide_index=True)

    if not data.empty:
        st.markdown("### Delete Preference")
        delete_id = st.number_input("Enter Preference ID to Delete", min_value=1, step=1, key="delete_preference_id")

        if st.button("Delete Selected Preference", use_container_width=True):
            execute("DELETE FROM faculty_preferences WHERE id=?", (int(delete_id),))
            st.success("Faculty preference deleted.")
            st.rerun()



def department_management_page():
    header()
    st.subheader("Department Management")

    with st.form("department_form"):
        c1, c2, c3 = st.columns(3)
        department_name = c1.text_input("Department Name", "CSE")
        hod_name = c2.text_input("HOD Name", "")
        status = c3.selectbox("Status", ["Active", "Inactive"])

        if st.form_submit_button("Save Department", use_container_width=True):
            try:
                execute(
                    "INSERT INTO departments(department_name, hod_name, status) VALUES(?,?,?)",
                    (department_name, hod_name, status)
                )
                log_action("Department Added", department_name)
                st.success("Department saved.")
                st.rerun()
            except sqlite3.IntegrityError:
                execute(
                    "UPDATE departments SET hod_name=?, status=? WHERE department_name=?",
                    (hod_name, status, department_name)
                )
                log_action("Department Updated", department_name)
                st.success("Department updated.")
                st.rerun()

    df = query_df("SELECT * FROM departments ORDER BY department_name")
    st.dataframe(df, use_container_width=True, hide_index=True)


def academic_year_page():
    header()
    st.subheader("Academic Year & Semester Management")

    with st.form("academic_year_form"):
        c1, c2, c3 = st.columns(3)
        year_name = c1.text_input("Academic Year", "2026-2027")
        semester_type = c2.selectbox("Semester Type", ["Odd Semester", "Even Semester"])
        is_active = c3.checkbox("Set as Active Academic Term")

        if st.form_submit_button("Save Academic Term", use_container_width=True):
            if is_active:
                execute("UPDATE academic_years SET is_active=0")
            try:
                execute(
                    "INSERT INTO academic_years(year_name, semester_type, is_active) VALUES(?,?,?)",
                    (year_name, semester_type, 1 if is_active else 0)
                )
                log_action("Academic Term Added", f"{year_name} {semester_type}")
                st.success("Academic term saved.")
                st.rerun()
            except sqlite3.IntegrityError:
                execute(
                    "UPDATE academic_years SET is_active=? WHERE year_name=? AND semester_type=?",
                    (1 if is_active else 0, year_name, semester_type)
                )
                log_action("Academic Term Updated", f"{year_name} {semester_type}")
                st.success("Academic term updated.")
                st.rerun()

    st.dataframe(query_df("SELECT * FROM academic_years ORDER BY id DESC"), use_container_width=True, hide_index=True)


def approval_workflow_page():
    header()
    st.subheader("📋 Timetable Approval Workflow")

    sdf = section_label_df()
    if sdf.empty:
        st.warning("Add sections first.")
        return

    section_name = st.selectbox("Select Class / Section", sdf["label"].tolist())
    section_id = int(sdf[sdf["label"] == section_name]["id"].iloc[0])

    approval = query_df(
        "SELECT * FROM timetable_approvals WHERE section_id=?",
        (section_id,)
    )

    if approval.empty:
        execute(
            "INSERT OR IGNORE INTO timetable_approvals(section_id, status, updated_at) VALUES(?,?,?)",
            (section_id, "Draft", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        current_status = "Draft"
    else:
        current_status = approval.iloc[0]["status"]

    st.info(f"Current Status: {current_status}")

    role = st.session_state.get("role", "Admin")
    username = st.session_state.get("username", "admin")

    st.markdown("### Approval Actions")

    if current_status == "Draft":
        if st.button("Submit to HOD", use_container_width=True):
            execute(
                "UPDATE timetable_approvals SET status=?, updated_at=? WHERE section_id=?",
                ("Submitted to HOD", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), section_id)
            )
            st.success("Submitted to HOD.")
            st.rerun()

    elif current_status == "Submitted to HOD":
        if role in ["Admin", "HOD"]:
            hod_comment = st.text_area("HOD Comment")
            if st.button("Approve by HOD", use_container_width=True):
                execute(
                    "UPDATE timetable_approvals SET status=?, hod_comment=?, updated_at=? WHERE section_id=?",
                    ("Approved by HOD", hod_comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), section_id)
                )
                st.success("Approved by HOD.")
                st.rerun()
        else:
            st.warning("Waiting for HOD approval.")

    elif current_status == "Approved by HOD":
        if role in ["Admin", "Principal"]:
            principal_comment = st.text_area("Principal Comment")
            if st.button("Approve by Principal", use_container_width=True):
                execute(
                    "UPDATE timetable_approvals SET status=?, principal_comment=?, updated_at=? WHERE section_id=?",
                    ("Approved by Principal", principal_comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), section_id)
                )
                st.success("Approved by Principal.")
                st.rerun()
        else:
            st.warning("Waiting for Principal approval.")

    elif current_status == "Approved by Principal":
        if role in ["Admin", "Principal"]:
            if st.button("Publish Timetable", use_container_width=True):
                execute(
                    "UPDATE timetable_approvals SET status=?, updated_at=? WHERE section_id=?",
                    ("Published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), section_id)
                )
                execute("UPDATE sections SET is_published=1 WHERE id=?", (section_id,))
                st.success("Timetable Published.")
                st.rerun()

    elif current_status == "Published":
        st.success("✅ Timetable already published.")

        if role == "Admin":
            if st.button("Reset to Draft", use_container_width=True):
                execute(
                    "UPDATE timetable_approvals SET status=?, updated_at=? WHERE section_id=?",
                    ("Draft", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), section_id)
                )
                execute("UPDATE sections SET is_published=0 WHERE id=?", (section_id,))
                st.warning("Reset to Draft.")
                st.rerun()

    st.markdown("### Approval Records")

    df = query_df("""
        SELECT ta.id, sec.year, sec.department, sec.semester, sec.section,
               ta.status, ta.hod_comment, ta.principal_comment, ta.updated_at
        FROM timetable_approvals ta
        JOIN sections sec ON ta.section_id = sec.id
        ORDER BY ta.id DESC
    """)

    st.dataframe(df, use_container_width=True, hide_index=True)


def auto_clash_resolver_page():
    header()
    st.subheader("Auto Clash Resolver")

    faculty_clashes, room_clashes, section_clashes = compute_clash_counts()
    total = faculty_clashes + room_clashes + section_clashes

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faculty Clashes", faculty_clashes)
    c2.metric("Room/Lab Clashes", room_clashes)
    c3.metric("Class Clashes", section_clashes)
    c4.metric("Total Clashes", total)

    st.info("Auto resolver clears the selected class timetable and regenerates using all current constraints.")

    sdf = section_label_df()
    if sdf.empty:
        st.warning("Add sections first.")
        return

    section_name = st.selectbox("Select Class to Resolve", sdf["label"].tolist())
    selected = sdf[sdf["label"] == section_name].iloc[0]
    section_id = int(selected["id"])

    if st.button("Analyze & Auto Resolve Selected Class", use_container_width=True):
        ok, msg = generate_for_section(section_id, int(selected["working_days"]), clear_old=True)
        log_action("Auto Clash Resolver", section_name)
        if ok:
            st.success("Regenerated successfully. " + msg)
        else:
            st.error(msg)


def student_portal_page():
    header()
    st.subheader("Student View Only Portal")

    sdf = section_label_df()
    if sdf.empty:
        st.warning("No timetable available.")
        return

    label = st.selectbox("Select Class / Section", sdf["label"].tolist())
    section_id = int(sdf[sdf["label"] == label]["id"].iloc[0])

    pub = query_df("SELECT is_published FROM sections WHERE id=?", (section_id,))
    if not pub.empty and int(pub.iloc[0]["is_published"] or 0) == 0:
        st.warning("This timetable is not yet published. Admin/HOD can still preview it.")

    df = timetable_detail(section_id=section_id)
    pivot = make_pivot(df)
    st.dataframe(pivot, use_container_width=True)

    if not df.empty:
        pdf = create_pdf(f"{label} - Student Timetable", df, pivot)
        st.download_button(
            "Download Student Timetable PDF",
            data=pdf,
            file_name=f"{label.replace(' ', '_')}_Student_Timetable.pdf",
            mime="application/pdf" if REPORTLAB_AVAILABLE else "text/plain",
            use_container_width=True
        )


def faculty_swap_requests_page():
    header()
    st.subheader("Faculty Swap Requests")

    fdf = faculty_df()
    if fdf.empty:
        st.warning("Add faculty first.")
        return

    with st.form("swap_request_form"):
        faculty_name = st.selectbox("Faculty", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])
        request_details = st.text_area("Swap Request Details", "I request to swap ...")

        if st.form_submit_button("Submit Swap Request", use_container_width=True):
            execute(
                "INSERT INTO faculty_swap_requests(faculty_id, request_details, status, created_at) VALUES(?,?,?,?)",
                (faculty_id, request_details, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            log_action("Swap Request Created", faculty_name)
            st.success("Swap request submitted.")
            st.rerun()

    df = query_df("""
        SELECT fs.id, f.name AS faculty, fs.request_details, fs.status, fs.created_at
        FROM faculty_swap_requests fs
        JOIN faculty f ON fs.faculty_id=f.id
        ORDER BY fs.id DESC
    """)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        c1, c2 = st.columns(2)
        req_id = c1.number_input("Request ID", min_value=1, step=1)
        status = c2.selectbox("Update Status", ["Pending", "Approved", "Rejected"])
        if st.button("Update Swap Request Status", use_container_width=True):
            execute("UPDATE faculty_swap_requests SET status=? WHERE id=?", (status, int(req_id)))
            log_action("Swap Request Status Updated", f"ID {req_id}: {status}")
            st.success("Status updated.")
            st.rerun()


def leave_management_page():
    header()
    st.subheader("Leave Management Integration")

    fdf = faculty_df()
    if fdf.empty:
        st.warning("Add faculty first.")
        return

    with st.form("leave_form"):
        c1, c2, c3 = st.columns(3)
        faculty_name = c1.selectbox("Faculty", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])
        day = c2.selectbox("Leave Day", DAYS)
        period = c3.selectbox("Affected Period", [0] + [p for p, _ in PERIODS], format_func=lambda x: "Full Day" if x == 0 else f"Period {x}")
        reason = st.text_input("Reason", "On leave")

        if st.form_submit_button("Submit Leave", use_container_width=True):
            execute("INSERT INTO faculty_leave(faculty_id, day, period, reason, status) VALUES(?,?,?,?,?)", (faculty_id, day, period, reason, "Pending"))
            log_action("Leave Submitted", faculty_name)
            st.success("Leave request saved.")
            st.rerun()

    df = query_df("""
        SELECT fl.id, f.name AS faculty, fl.day, fl.period, fl.reason, fl.status
        FROM faculty_leave fl
        JOIN faculty f ON fl.faculty_id=f.id
        ORDER BY fl.id DESC
    """)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        leave_id = st.number_input("Leave ID to update", min_value=1, step=1)
        status = st.selectbox("Leave Status", ["Pending", "Approved", "Rejected"])
        if st.button("Update Leave Status", use_container_width=True):
            execute("UPDATE faculty_leave SET status=? WHERE id=?", (status, int(leave_id)))
            log_action("Leave Status Updated", f"ID {leave_id}: {status}")
            st.success("Leave status updated.")
            st.rerun()


def attendance_page():
    header()
    st.subheader("Attendance Integration")

    df = timetable_detail()
    if df.empty:
        st.warning("Generate timetable first.")
        return

    df["display"] = df.apply(lambda x: f"ID {x['id']} | {x['day']} P{x['period']} | {x['subject_name']} | {x['faculty']}", axis=1)

    with st.form("attendance_form"):
        selected = st.selectbox("Select Timetable Slot", df["display"].tolist())
        timetable_id = int(selected.split("|")[0].replace("ID", "").strip())
        attendance_date = st.date_input("Date")
        status = st.selectbox("Status", ["Conducted", "Cancelled", "Substituted"])
        remarks = st.text_input("Remarks", "")

        if st.form_submit_button("Save Attendance Entry", use_container_width=True):
            execute(
                "INSERT INTO attendance(timetable_id, attendance_date, status, remarks, created_at) VALUES(?,?,?,?,?)",
                (timetable_id, str(attendance_date), status, remarks, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            log_action("Attendance Saved", f"Timetable ID {timetable_id}")
            st.success("Attendance entry saved.")
            st.rerun()

    data = query_df("""
        SELECT a.id, a.attendance_date, a.status, a.remarks,
               t.day, t.period, s.subject_name, f.name AS faculty
        FROM attendance a
        JOIN timetable t ON a.timetable_id=t.id
        JOIN subjects s ON t.subject_id=s.id
        JOIN faculty f ON t.faculty_id=f.id
        ORDER BY a.id DESC
    """)
    st.dataframe(data, use_container_width=True, hide_index=True)


def exam_timetable_page():
    header()
    st.subheader("Exam Timetable Generator")

    sdf = section_label_df()
    rdf = rooms_df()

    if sdf.empty:
        st.warning("Add sections first.")
        return

    section_name = st.selectbox("Class / Section", sdf["label"].tolist())
    section_id = int(sdf[sdf["label"] == section_name]["id"].iloc[0])
    subdf = subject_label_df(section_id)

    if subdf.empty:
        st.warning("Add subjects for this section first.")
        return

    with st.form("exam_form"):
        exam_type = st.selectbox(
            "Exam Type",
            ["CIA 1", "CIA 2", "Model Examination", "University Examination"]
        )

        subject_label = st.selectbox("Subject", subdf["label"].tolist())
        subject_id = int(subdf[subdf["label"] == subject_label]["id"].iloc[0])

        exam_date = st.date_input("Exam Date")
        exam_time = st.text_input("Exam Time", "10:00 AM - 01:00 PM")

        room_name = st.selectbox("Room", ["None"] + rdf["room_name"].tolist())
        room_id = None if room_name == "None" else int(rdf[rdf["room_name"] == room_name]["id"].iloc[0])

        if st.form_submit_button("Save Exam Timetable", use_container_width=True):
            execute(
                """
                INSERT INTO exam_timetable(
                    section_id, subject_id, exam_type, exam_date, exam_time, room_id
                )
                VALUES(?,?,?,?,?,?)
                """,
                (section_id, subject_id, exam_type, str(exam_date), exam_time, room_id)
            )
            log_action("Exam Timetable Added", f"{exam_type} - {subject_label}")
            st.success("Exam timetable saved.")
            st.rerun()

    data = query_df("""
        SELECT et.id, et.exam_type,
               sec.year, sec.department, sec.semester, sec.section,
               s.subject_code, s.subject_name,
               et.exam_date, et.exam_time,
               COALESCE(r.room_name, '') AS room
        FROM exam_timetable et
        JOIN sections sec ON et.section_id=sec.id
        JOIN subjects s ON et.subject_id=s.id
        LEFT JOIN rooms r ON et.room_id=r.id
        ORDER BY et.exam_type, et.exam_date
    """)

    st.dataframe(data, use_container_width=True, hide_index=True)

def audit_log_page():
    header()
    st.subheader("Audit Log")

    df = query_df("SELECT * FROM audit_log ORDER BY id DESC LIMIT 500")
    st.dataframe(df, use_container_width=True, hide_index=True)


def excel_import_page():
    header()
    st.subheader("Excel Import")

    st.info("Upload Excel files with sheets named Faculty, Sections, Rooms, Subjects. Columns must match existing table fields.")

    uploaded = st.file_uploader("Upload Excel Template", type=["xlsx"], key="excel_import_file")
    if uploaded is not None:
        try:
            xls = pd.ExcelFile(uploaded)
            st.write("Detected sheets:", xls.sheet_names)

            if st.button("Import Excel Data", use_container_width=True):
                if "Faculty" in xls.sheet_names:
                    df = pd.read_excel(xls, "Faculty")
                    for _, r in df.iterrows():
                        execute(
                            "INSERT OR IGNORE INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)",
                            (str(r.get("name", "")), str(r.get("designation", "")), str(r.get("department", "")), int(r.get("max_hours", 24)))
                        )

                if "Rooms" in xls.sheet_names:
                    df = pd.read_excel(xls, "Rooms")
                    for _, r in df.iterrows():
                        execute(
                            "INSERT OR IGNORE INTO rooms(room_name, room_type, capacity, equipment, department) VALUES(?,?,?,?,?)",
                            (
                                str(r.get("room_name", "")),
                                str(r.get("room_type", "Classroom")),
                                int(r.get("capacity", 60)),
                                str(r.get("equipment", "")),
                                str(r.get("department", current_department() or "CSE"))
                            )
                        )

                if "Sections" in xls.sheet_names:
                    df = pd.read_excel(xls, "Sections")
                    for _, r in df.iterrows():
                        execute(
                            "INSERT OR IGNORE INTO sections(year, department, semester, section, working_days) VALUES(?,?,?,?,?)",
                            (str(r.get("year", "")), str(r.get("department", "")), str(r.get("semester", "")), str(r.get("section", "")), int(r.get("working_days", 6)))
                        )

                log_action("Excel Import", ",".join(xls.sheet_names))
                st.success("Excel import completed.")
                st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")
            
def leave_alteration_page():
    header()
    st.subheader("Faculty Leave → Alter Class → HOD Approval")

    fdf = faculty_df()

    if fdf.empty:
        st.warning("Add faculty first.")
        return

    st.markdown("### Apply Leave with Mandatory Alteration")

    with st.form("leave_alter_form"):
        c1, c2, c3 = st.columns(3)

        faculty_name = c1.selectbox("Faculty Applying Leave", fdf["name"].tolist())
        faculty_id = int(fdf[fdf["name"] == faculty_name]["id"].iloc[0])

        leave_day = c2.selectbox("Leave Day", DAYS)
        leave_period = c3.selectbox(
            "Leave Period",
            [0] + [p for p, _ in PERIODS],
            format_func=lambda x: "Full Day" if x == 0 else f"Period {x}"
        )

        reason = st.text_input("Reason", "Faculty on leave")

        submitted = st.form_submit_button("Check Periods & Submit Leave")

    if submitted:
        if leave_period == 0:
            affected = query_df("""
                SELECT t.id, t.day, t.period, t.timing, s.subject_name
                FROM timetable t
                JOIN subjects s ON t.subject_id=s.id
                WHERE t.faculty_id=? AND t.day=?
                ORDER BY t.period
            """, (faculty_id, leave_day))
        else:
            affected = query_df("""
                SELECT t.id, t.day, t.period, t.timing, s.subject_name
                FROM timetable t
                JOIN subjects s ON t.subject_id=s.id
                WHERE t.faculty_id=? AND t.day=? AND t.period=?
                ORDER BY t.period
            """, (faculty_id, leave_day, leave_period))

        st.session_state.leave_check = {
            "faculty_id": faculty_id,
            "faculty_name": faculty_name,
            "leave_day": leave_day,
            "leave_period": leave_period,
            "reason": reason,
            "affected": affected
        }

    if "leave_check" in st.session_state:
        data = st.session_state.leave_check
        affected = data["affected"]

        if affected.empty:
            st.success("No classes found on selected leave period/day. Leave can be submitted directly.")

            if st.button("Submit Leave Without Alteration", use_container_width=True):
                execute(
                    "INSERT INTO faculty_leave(faculty_id, day, period, reason, status) VALUES(?,?,?,?,?)",
                    (data["faculty_id"], data["leave_day"], data["leave_period"], data["reason"], "Pending")
                )
                st.success("Leave request submitted to HOD.")
                del st.session_state.leave_check
                st.rerun()

        else:
            st.error(
                f"{data['faculty_name']} has {len(affected)} class period(s) on {data['leave_day']}. "
                "Alter faculty must be selected before submitting leave."
            )

            st.dataframe(affected, use_container_width=True, hide_index=True)

            st.markdown("### Select Substitute Faculty")

            substitute_map = {}

            for _, row in affected.iterrows():
                period = int(row["period"])

                available = query_df("""
                    SELECT id, name
                    FROM faculty
                    WHERE id != ?
                    AND id NOT IN (
                        SELECT faculty_id FROM timetable
                        WHERE day=? AND period=?
                    )
                    AND id NOT IN (
                        SELECT faculty_id FROM faculty_unavailable
                        WHERE day=? AND period=?
                    )
                    ORDER BY name
                """, (
                    data["faculty_id"],
                    data["leave_day"], period,
                    data["leave_day"], period
                ))

                if available.empty:
                    st.warning(f"No free substitute faculty available for Period {period}.")
                    substitute_map[int(row["id"])] = None
                else:
                    sub_name = st.selectbox(
                        f"Substitute for Period {period} - {row['subject_name']}",
                        available["name"].tolist(),
                        key=f"substitute_{row['id']}"
                    )
                    substitute_id = int(available[available["name"] == sub_name]["id"].iloc[0])
                    substitute_map[int(row["id"])] = substitute_id

            if st.button("Submit Leave With Alteration Request", use_container_width=True):
                if any(v is None for v in substitute_map.values()):
                    st.error("Please select substitute faculty for all affected periods.")
                    return

                execute(
                    "INSERT INTO faculty_leave(faculty_id, day, period, reason, status) VALUES(?,?,?,?,?)",
                    (data["faculty_id"], data["leave_day"], data["leave_period"], data["reason"], "Pending")
                )

                leave_id = query_df("SELECT MAX(id) AS id FROM faculty_leave").iloc[0]["id"]

                for _, row in affected.iterrows():
                    timetable_id = int(row["id"])
                    substitute_id = substitute_map[timetable_id]

                    execute("""
                        INSERT INTO leave_alteration_requests(
                            leave_id, timetable_id, original_faculty_id,
                            substitute_faculty_id, day, period, status, created_at
                        )
                        VALUES(?,?,?,?,?,?,?,?)
                    """, (
                        int(leave_id),
                        timetable_id,
                        data["faculty_id"],
                        substitute_id,
                        data["leave_day"],
                        int(row["period"]),
                        "Pending",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

                st.success("Leave and alteration request submitted to HOD for approval.")
                del st.session_state.leave_check
                st.rerun()

    st.markdown("### HOD Approval Panel")

    requests = query_df("""
        SELECT lar.id, lar.leave_id, of.name AS original_faculty,
               sf.name AS substitute_faculty,
               lar.day, lar.period, lar.status, lar.hod_remark,
               s.subject_name
        FROM leave_alteration_requests lar
        JOIN faculty of ON lar.original_faculty_id=of.id
        JOIN faculty sf ON lar.substitute_faculty_id=sf.id
        JOIN timetable t ON lar.timetable_id=t.id
        JOIN subjects s ON t.subject_id=s.id
        ORDER BY lar.id DESC
    """)

    st.dataframe(requests, use_container_width=True, hide_index=True)

    if not requests.empty:
        req_id = st.number_input("Enter Alteration Request ID", min_value=1, step=1)
        action = st.selectbox("HOD Action", ["Approve", "Reject"])
        remark = st.text_input("HOD Remark", "")

        if st.button("Submit HOD Decision", use_container_width=True):
            status = "Approved" if action == "Approve" else "Rejected"

            execute(
                "UPDATE leave_alteration_requests SET status=?, hod_remark=? WHERE id=?",
                (status, remark, int(req_id))
            )

            leave_id_df = query_df(
                "SELECT leave_id FROM leave_alteration_requests WHERE id=?",
                (int(req_id),)
            )

            if not leave_id_df.empty:
                leave_id = int(leave_id_df.iloc[0]["leave_id"])

                pending = query_df("""
                    SELECT id FROM leave_alteration_requests
                    WHERE leave_id=? AND status='Pending'
                """, (leave_id,))

                rejected = query_df("""
                    SELECT id FROM leave_alteration_requests
                    WHERE leave_id=? AND status='Rejected'
                """, (leave_id,))

                if not rejected.empty:
                    execute("UPDATE faculty_leave SET status=? WHERE id=?", ("Rejected", leave_id))
                elif pending.empty:
                    execute("UPDATE faculty_leave SET status=? WHERE id=?", ("Approved", leave_id))

            st.success("HOD decision updated.")
            st.rerun()
            
def settings_page():
    header()
    st.subheader("Settings")

    if st.button("Load Sample Data"):
        execute("INSERT OR IGNORE INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)", ("G Gokulraj", "AP/CSE", "CSE", 24))
        execute("INSERT OR IGNORE INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)", ("Faculty 2", "AP/CSE", "CSE", 24))
        execute("INSERT OR IGNORE INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)", ("Lab Faculty", "AP/CSE", "CSE", 24))
        execute("INSERT OR IGNORE INTO rooms(room_name, room_type, capacity, equipment) VALUES(?,?,?,?)", ("CSE A Classroom", "Classroom", 60, "Projector"))
        execute("INSERT OR IGNORE INTO rooms(room_name, room_type, capacity, equipment) VALUES(?,?,?,?)", ("Programming Lab 1", "Lab", 60, "60 Systems"))
        execute("INSERT OR IGNORE INTO sections(year, department, semester, section, working_days) VALUES(?,?,?,?,?)", ("2nd Year", "CSE", "III", "A", 6))
        st.success("Sample data loaded.")

    if st.button("Reset All Master Data and Timetable"):
        for table in ["timetable", "subjects", "rooms", "sections", "faculty_unavailable", "faculty_preferences", "faculty"]:
            execute(f"DELETE FROM {table}")
        st.warning("All data cleared.")

    # DATABASE BACKUP
    st.markdown("### Database Backup")

    if Path("timetable.db").exists():
        with open("timetable.db", "rb") as f:
            st.download_button(
                "Download Backup",
                data=f,
                file_name="timetable_backup.db",
                mime="application/octet-stream",
                use_container_width=True
            )


    st.markdown("### Database Restore")
    restore_file = st.file_uploader("Upload timetable_backup.db to restore", type=["db"], key="restore_db_file")
    if restore_file is not None:
        st.warning("Restoring will replace the current database. Use only your valid backup file.")
        if st.button("Restore Database", use_container_width=True):
            with open(DB_NAME, "wb") as f:
                f.write(restore_file.getbuffer())
            st.success("Database restored successfully. Please refresh the app.")
            st.rerun()

def user_management_page():
    header()
    st.subheader("User Management")

    st.info("Admin can create login accounts for Principal, HOD, Coordinator, Faculty, and Student.")

    with st.form("create_user_form"):
        c1, c2, c3 = st.columns(3)

        username = c1.text_input("Username")
        password = c2.text_input("Password", type="password")
        role = c3.selectbox(
            "Role",
            ["Admin", "Principal", "HOD", "Coordinator", "Faculty", "Student"]
        )

        c4, c5 = st.columns(2)
        name = c4.text_input("Full Name")
        department = c5.selectbox(
            "Department",
            ["Administration", "CSE", "IT", "AI&DS", "ECE", "EEE", "MECH"]
        )

        submitted = st.form_submit_button("Create User Login", use_container_width=True)

        if submitted:
            if not username or not password or not name:
                st.error("Username, Password, and Full Name are required.")
            else:
                try:
                    execute(
                        "INSERT INTO users(username, password, role, name, department) VALUES(?,?,?,?,?)",
                        (username.strip(), password.strip(), role, name.strip(), department)
                    )
                    log_action("User Created", f"{username} - {role} - {department}")
                    st.success(f"User login created successfully for {name}.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Username already exists. Please use another username.")

    st.divider()

    st.subheader("Existing Users")

    users = query_df("""
        SELECT id, username, role, name, department
        FROM users
        ORDER BY role, department, username
    """)

    st.dataframe(users, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Update / Delete User")

    if not users.empty:
        user_options = users["username"].tolist()
        selected_username = st.selectbox("Select User", user_options)

        selected = users[users["username"] == selected_username].iloc[0]

        with st.form("update_user_form"):
            c1, c2, c3 = st.columns(3)

            new_name = c1.text_input("Name", selected["name"])
            new_role = c2.selectbox(
                "Role",
                ["Admin", "Principal", "HOD", "Coordinator", "Faculty", "Student"],
                index=["Admin", "Principal", "HOD", "Coordinator", "Faculty", "Student"].index(selected["role"])
                if selected["role"] in ["Admin", "Principal", "HOD", "Coordinator", "Faculty", "Student"] else 0
            )
            new_department = c3.selectbox(
                "Department",
                ["Administration", "CSE", "IT", "AI&DS", "ECE", "EEE", "MECH"],
                index=["Administration", "CSE", "IT", "AI&DS", "ECE", "EEE", "MECH"].index(selected["department"])
                if selected["department"] in ["Administration", "CSE", "IT", "AI&DS", "ECE", "EEE", "MECH"] else 0
            )

            new_password = st.text_input(
                "New Password - leave blank to keep old password",
                type="password"
            )

            update_btn = st.form_submit_button("Update User", use_container_width=True)

            if update_btn:
                if new_password.strip():
                    execute(
                        "UPDATE users SET password=?, role=?, name=?, department=? WHERE username=?",
                        (new_password.strip(), new_role, new_name.strip(), new_department, selected_username)
                    )
                else:
                    execute(
                        "UPDATE users SET role=?, name=?, department=? WHERE username=?",
                        (new_role, new_name.strip(), new_department, selected_username)
                    )

                log_action("User Updated", selected_username)
                st.success("User updated successfully.")
                st.rerun()

        st.warning("Delete user only if the account is no longer required.")

        if st.button("Delete Selected User", use_container_width=True):
            if selected_username == st.session_state.get("username"):
                st.error("You cannot delete your own logged-in account.")
            elif selected_username == "admin":
                st.error("Default admin account cannot be deleted.")
            else:
                execute("DELETE FROM users WHERE username=?", (selected_username,))
                log_action("User Deleted", selected_username)
                st.success("User deleted successfully.")
                st.rerun()

def main_app():
    page = sidebar_menu()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Department Management":
        department_management_page()
    elif page == "Academic Year":
        academic_year_page()
    elif page == "Faculty":
        faculty_page()
    elif page == "Sections":
        sections_page()
    elif page == "Infrastructure":
        rooms_page()
    elif page == "Subjects & Constraints":
        subjects_page()
    elif page == "Generate Timetable":
        generate_page()
    elif page == "Auto Clash Resolver":
        auto_clash_resolver_page()
    elif page == "Manual Entry":
        manual_entry_page()
    elif page == "Delete / Reset":
        delete_reset_page()
    elif page == "View / Export":
        view_export_page()
    elif page == "Clash Intelligence":
        clash_page()
    elif page == "Faculty Workload":
        workload_page()
    elif page == "Faculty Unavailable":
        faculty_unavailable_page()
    elif page == "Faculty Preferences":
        faculty_preferences_page()
    elif page == "Approval Workflow":
        approval_workflow_page()
    elif page == "Student Portal":
        student_portal_page()
    elif page == "Faculty Swap Requests":
        faculty_swap_requests_page()
    elif page == "Leave Management":
        leave_management_page()
    elif page == "Leave Alteration":
        leave_alteration_page()
    elif page == "Attendance":
        attendance_page()
    elif page == "Exam Timetable":
        exam_timetable_page()
    elif page == "Audit Log":
        audit_log_page()
    elif page == "Excel Import":
        excel_import_page()
    elif page == "Supabase Test":
        supabase_test_page()
    elif page == "Edit Records":
        edit_records_page()
    elif page == "User Management":
        user_management_page()
    elif page == "Settings":
        settings_page()

    st.markdown("""
    <hr style='border:1px solid #d4af37;'>

    <div style='text-align:center;
                color:#0b5d2a;
                font-size:14px;
                padding:10px;'>

    <b>SRIT Academic Resource Management System (SARMS)</b><br>
    Academic Year 2026–2027<br>
    Developed by Department of Computer Science and Engineering<br>
    Sri Ramakrishna Institute of Technology, Coimbatore

    </div>
    """, unsafe_allow_html=True)


init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = ""
if "username" not in st.session_state:
    st.session_state.username = ""

if st.session_state.logged_in:
    main_app()
else:
    login_page()
