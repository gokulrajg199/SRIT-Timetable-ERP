
import streamlit as st
import sqlite3
import pandas as pd
import random
from io import BytesIO
from datetime import datetime
from pathlib import Path

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

/* GLOBAL FONT */
html, body, [class*="css"]{
    font-size:18px !important;
    font-weight:500 !important;
}

/* APP BACKGROUND */
.stApp{
    background:#f4fbf6;
    color:#111111;
}

/* HEADER */
.main-header{
    background:linear-gradient(135deg,#1b5e20,#2e7d32,#43a047);
    color:white !important;
    padding:24px;
    border-radius:18px;
    border:3px solid #d4af37;
    box-shadow:0px 5px 20px rgba(0,0,0,0.18);
    text-align:center;
    margin-bottom:20px;
}

.main-header h1{
    font-size:42px !important;
    font-weight:800 !important;
}

.main-header h2{
    font-size:34px !important;
    font-weight:700 !important;
}

.main-header h3,
.main-header h4,
.main-header p{
    color:white !important;
    margin:4px;
    font-size:22px !important;
}

/* SIDEBAR */
section[data-testid="stSidebar"]{
    background:#1b5e20;
}

section[data-testid="stSidebar"] *{
    color:white !important;
    font-size:18px !important;
    font-weight:600 !important;
}

/* PAGE TITLES */
h1{
    font-size:40px !important;
    font-weight:800 !important;
    color:#1b5e20 !important;
}

h2{
    font-size:34px !important;
    font-weight:700 !important;
    color:#1b5e20 !important;
}

h3{
    font-size:28px !important;
    font-weight:700 !important;
    color:#1b5e20 !important;
}

/* LABELS */
label{
    font-size:18px !important;
    font-weight:600 !important;
}

/* METRICS */
div[data-testid="stMetric"]{
    background:white;
    border:2px solid #d4af37;
    border-left:7px solid #d4af37;
    border-radius:14px;
    padding:15px;
    box-shadow:0px 3px 12px rgba(0,0,0,0.08);
}

div[data-testid="stMetric"] label{
    font-size:18px !important;
    font-weight:700 !important;
}

div[data-testid="stMetricValue"]{
    font-size:32px !important;
    font-weight:800 !important;
}

/* BUTTONS */
.stButton button{
    background:linear-gradient(135deg,#2e7d32,#43a047);
    color:white !important;
    border:2px solid #d4af37;
    border-radius:10px;
    font-weight:bold;
    font-size:18px !important;
}

.stDownloadButton button{
    background:#d4af37;
    color:#111111 !important;
    border-radius:10px;
    font-weight:bold;
    font-size:18px !important;
}

/* INPUT BOXES */
input{
    font-size:18px !important;
    font-weight:600 !important;
}

/* SELECT BOX */
div[data-baseweb="select"]{
    font-size:18px !important;
}

/* DATAFRAMES */
div[data-testid="stDataFrame"] table{
    font-size:20px !important;
    font-weight:600 !important;
}

div[data-testid="stDataFrame"] th{
    text-align:center !important;
    font-size:22px !important;
    font-weight:800 !important;
    background:#1b5e20 !important;
    color:white !important;
}

div[data-testid="stDataFrame"] td{
    text-align:center !important;
    font-size:18px !important;
    font-weight:600 !important;
}

/* CARDS */
.card{
    background:white;
    border:2px solid #d4af37;
    border-radius:16px;
    padding:18px;
    box-shadow:0px 3px 12px rgba(0,0,0,0.08);
    margin-bottom:14px;
}

/* INFO BOX */
.success-box{
    background:#e8f5e9;
    color:#1b5e20;
    padding:12px;
    border-radius:10px;
    border-left:5px solid #2e7d32;
    font-size:18px;
}

.warning-box{
    background:#fff8e1;
    color:#7a5800;
    padding:12px;
    border-radius:10px;
    border-left:5px solid #d4af37;
    font-size:18px;
}

/* TIMETABLE COLORS */
.metric-icon{
    font-size:28px;
    font-weight:800;
    color:#1b5e20;
}

.theory-cell{
    background:#e3f2fd;
    color:#0d47a1;
}

.lab-cell{
    background:#e8f5e9;
    color:#1b5e20;
}

.practical-cell{
    background:#fff3e0;
    color:#e65100;
}

.manual-cell{
    background:#fff8e1;
    color:#7a5800;
}

</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def connect_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def execute(query, params=()):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(query, params)
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

    conn.commit()
    conn.close()

    add_col("sections", "year", "TEXT")
    add_col("rooms", "capacity", "INTEGER DEFAULT 60")
    add_col("rooms", "equipment", "TEXT DEFAULT ''")
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
    return query_df("""
        SELECT id,
               COALESCE(year,'') || ' | ' || department || ' | Sem ' || semester || ' | Sec ' || section AS label,
               working_days
        FROM sections
        ORDER BY year, department, semester, section
    """)


def faculty_df():
    return query_df("SELECT id, name FROM faculty ORDER BY name")


def rooms_df(room_type=None):
    if room_type:
        return query_df("SELECT id, room_name, room_type FROM rooms WHERE room_type=? ORDER BY room_name", (room_type,))
    return query_df("SELECT id, room_name, room_type FROM rooms ORDER BY room_name")


def subject_label_df(section_id=None):
    if section_id:
        return query_df("SELECT id, subject_code || ' - ' || subject_name AS label FROM subjects WHERE section_id=? ORDER BY subject_name", (section_id,))
    return query_df("SELECT id, subject_code || ' - ' || subject_name AS label FROM subjects ORDER BY subject_name")


from pathlib import Path

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
    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Admin Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", use_container_width=True):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid username or password")
        st.info("Default: admin / admin123")
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

        # Same theory subject max 2 periods per day.
        if not is_lab:
            current_same_subject = section_day_subject_theory.get((day, sid), 0)
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
            if grid.get((day, p)) is not None:
                return False
            if (day, p, fid) in used_faculty:
                return False
            if room_id and (day, p, room_id) in used_room:
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

        while hours_left > 0 and attempts < 1800:
            attempts += 1

            if session["session_type"] == "Lab":
                length = min(int(session["continuous_hours"]), hours_left, 4)
            elif session["continuous_required"]:
                length = min(int(session["continuous_hours"]), hours_left, 2)
            else:
                length = 1

            possible_starts = [p for p, _ in PERIODS if p + length - 1 <= 8]
            random.shuffle(possible_starts)
            candidate_days = days[:]
            random.shuffle(candidate_days)

            placed = False
            for day in candidate_days:
                for start in possible_starts:
                    if can_place(day, start, length, session):
                        place(day, start, length, session)
                        hours_left -= length
                        placed = True
                        break
                if placed:
                    break

            if not placed and attempts > 1500:
                return False, (
                    f"Unable to place {session['subject_name']} ({session['session_type']}). "
                    "Check rules: faculty max theory/day=3, lab/day=1, lab max=4, "
                    "if lab exists theory max=2, no same subject theory+lab on same day."
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
    with st.sidebar:
        st.title("SRIT ERP")
        page = st.radio("Menu", [
            "Dashboard", "Faculty", "Sections", "Infrastructure",
            "Subjects & Constraints", "Generate Timetable", "Manual Entry",
            "Delete / Reset", "View / Export", "Clash Intelligence",
            "Faculty Workload", "Edit Records", "Settings"
        ])
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    return page


def dashboard_page():
header()

```
faculty_clashes, room_clashes, section_clashes = compute_clash_counts()
total_clashes = faculty_clashes + room_clashes + section_clashes

c1, c2, c3, c4 = st.columns(4)
c5, c6, c7, c8 = st.columns(4)

c1.metric("👨‍🏫 Faculty", len(query_df("SELECT id FROM faculty")))
c2.metric("🏫 Sections", len(query_df("SELECT id FROM sections")))
c3.metric("📚 Subjects", len(query_df("SELECT id FROM subjects")))
c4.metric("🚪 Classrooms", len(query_df("SELECT id FROM rooms WHERE room_type='Classroom'")))

c5.metric("🖥 Labs", len(query_df("SELECT id FROM rooms WHERE room_type='Lab'")))
c6.metric("⚙ Other Rooms", len(query_df("SELECT id FROM rooms WHERE room_type NOT IN ('Classroom','Lab')")))
c7.metric("📅 Entries", len(query_df("SELECT id FROM timetable")))
c8.metric("⚠ Clashes", total_clashes)

st.subheader("📊 Timetable Analytics")

workload, room_util, lab_util = analytics_data()

a1, a2, a3 = st.columns(3)

with a1:
    st.markdown("#### Faculty Workload Chart")
    if not workload.empty:
        st.bar_chart(workload.set_index("name"))
    else:
        st.info("No workload data yet.")

with a2:
    st.markdown("#### Room Utilization Chart")
    if not room_util.empty:
        st.bar_chart(room_util.set_index("room"))
    else:
        st.info("No room usage yet.")

with a3:
    st.markdown("#### Lab Utilization Chart")
    if not lab_util.empty:
        st.bar_chart(lab_util.set_index("lab"))
    else:
        st.info("No lab usage yet.")

st.subheader("⚠ Clash Summary Dashboard")

k1, k2, k3 = st.columns(3)
k1.metric("Faculty Clashes", faculty_clashes)
k2.metric("Room/Lab Clashes", room_clashes)
k3.metric("Class Clashes", section_clashes)

st.subheader("⏱ SRIT Academic Time Grid")

time_grid = pd.DataFrame(
    PERIODS,
    columns=["PERIOD", "TIMING"]
)

st.dataframe(
    time_grid,
    use_container_width=True,
    hide_index=True
)

st.markdown(
    """
    <div class='success-box'>
    Advanced rules enabled:
    Faculty theory max 3/day,
    Lab max 4/day,
    One lab per faculty/day,
    If lab exists theory max 2/day,
    No same subject theory and lab on same day.
    </div>
    """,
    unsafe_allow_html=True
)
```


def faculty_page():
    header()
    st.subheader("Faculty Management")

    with st.form("faculty_form"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Faculty Name")
        designation = c2.text_input("Designation", "AP/CSE")
        department = c3.text_input("Department", "CSE")
        max_hours = c4.number_input("Max Hours / Week", 1, 40, 24)
        if st.form_submit_button("Save Faculty", use_container_width=True) and name:
            try:
                execute("INSERT INTO faculty(name, designation, department, max_hours) VALUES(?,?,?,?)", (name, designation, department, max_hours))
                st.success("Faculty saved.")
            except sqlite3.IntegrityError:
                st.error("Faculty already exists.")

    st.dataframe(query_df("SELECT * FROM faculty ORDER BY name"), use_container_width=True, hide_index=True)


def sections_page():
    header()
    st.subheader("Class / Section Management")

    with st.form("section_form"):
        c1, c2, c3, c4, c5 = st.columns(5)

        year = c1.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        semester = c2.selectbox("Semester", ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"])
        department = c3.text_input("Department", "CSE")
        section = c4.text_input("Section", "A")
        working_days = c5.selectbox("Working Days", [5, 6], index=1)

        if st.form_submit_button("Save Class / Section", use_container_width=True):
            try:
                execute(
                    "INSERT INTO sections(year, department, semester, section, working_days) VALUES(?,?,?,?,?)",
                    (year, department, semester, section, working_days)
                )
                st.success("Section saved.")
            except sqlite3.IntegrityError:
                st.error("Section already exists.")

    st.dataframe(
        query_df("SELECT * FROM sections ORDER BY year, department, semester, section"),
        use_container_width=True,
        hide_index=True
    )


def rooms_page():
    header()
    st.subheader("Infrastructure Management")

    with st.form("room_form"):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.5])
        room_name = c1.text_input("Room / Lab Name")
        room_type = c2.selectbox("Type", ["Classroom", "Lab", "Seminar Hall", "Smart Classroom", "Other"])
        capacity = c3.number_input("Capacity", 1, 300, 60)
        equipment = c4.text_input("Equipment", "Projector")
        if st.form_submit_button("Save Infrastructure", use_container_width=True) and room_name:
            try:
                execute("INSERT INTO rooms(room_name, room_type, capacity, equipment) VALUES(?,?,?,?)", (room_name, room_type, capacity, equipment))
                st.success("Infrastructure saved.")
            except sqlite3.IntegrityError:
                st.error("Room / Lab already exists.")

    st.dataframe(query_df("SELECT * FROM rooms ORDER BY room_type, room_name"), use_container_width=True, hide_index=True)


def subjects_page():
    header()
    st.subheader("Subjects & Constraint Mapping")

    fdf = faculty_df()
    sdf = section_label_df()
    rdf = rooms_df()
    lab_rdf = query_df("SELECT id, room_name FROM rooms WHERE room_type='Lab' ORDER BY room_name")
    class_rdf = query_df("SELECT id, room_name FROM rooms WHERE room_type IN ('Classroom','Smart Classroom') ORDER BY room_name")

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
                theory_cont_hours = st.number_input(
                    "How many continuous theory periods?",
                    2,
                    8,
                    2
                )

        elif subject_type in ["Lab", "Practical"]:
            lab_hours = st.number_input("Lab Hours / Week", 1, 10, 4)
            weekly_hours = lab_hours

            st.info("Lab continuous period is mandatory.")
            lab_cont = True
            lab_cont_hours = st.number_input(
                "How many continuous lab periods?",
                1,
                8,
                lab_hours
            )

        elif subject_type == "Theory + Lab":
            c1, c2 = st.columns(2)

            theory_hours = c1.number_input("Theory Hours / Week", 1, 10, 2)
            lab_hours = c2.number_input("Lab Hours / Week", 1, 10, 2)
            weekly_hours = theory_hours + lab_hours

            same_day_theory = st.checkbox("Schedule All Theory Hours On Same Day?")
            theory_cont = st.checkbox("Theory Continuous Period Required?")

            if theory_cont:
                theory_cont_hours = st.number_input(
                    "How many continuous theory periods?",
                    2,
                    8,
                    2
                )

            st.info("Lab continuous period is mandatory for Theory + Lab.")
            lab_cont = True
            lab_cont_hours = st.number_input(
                "How many continuous lab periods?",
                1,
                8,
                lab_hours
            )

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

    st.dataframe(query_df("""
        SELECT s.id, s.subject_code, s.subject_name, s.subject_type,
               s.weekly_hours, s.theory_hours, s.lab_hours,
               s.theory_continuous_required, s.theory_continuous_hours,
               s.same_day_theory,
               s.lab_continuous_required, s.lab_continuous_hours,
               f.name AS theory_faculty, lf.name AS lab_faculty,
               sec.year, sec.department, sec.semester, sec.section,
               r.room_name AS classroom, lr.room_name AS lab
        FROM subjects s
        JOIN faculty f ON s.faculty_id=f.id
        LEFT JOIN faculty lf ON s.lab_faculty_id=lf.id
        JOIN sections sec ON s.section_id=sec.id
        LEFT JOIN rooms r ON s.room_id=r.id
        LEFT JOIN rooms lr ON s.lab_room_id=lr.id
        ORDER BY sec.year, sec.department, sec.semester, sec.section, s.subject_name
    """), use_container_width=True, hide_index=True)

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
                WHERE day=? AND period=? AND (section_id=? OR faculty_id=? OR (? IS NOT NULL AND room_id=?))
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

    clear_old = st.checkbox("Clear old timetable for this section before generating", value=True)

    if st.button("Generate Clash-Free Timetable", type="primary", use_container_width=True):
        ok, msg = generate_for_section(section_id, working_days, clear_old=clear_old)
        if ok:
            st.success(msg)
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
        for table in ["timetable", "subjects", "rooms", "sections", "faculty"]:
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

def main_app():
    page = sidebar_menu()

    if page == "Dashboard":
        dashboard_page()
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
    elif page == "Edit Records":
        edit_records_page()
    elif page == "Settings":
        settings_page()
    # FOOTER
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

if st.session_state.logged_in:
    main_app()
else:
    login_page()
