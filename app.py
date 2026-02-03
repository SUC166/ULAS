import streamlit as st
import pandas as pd
import os, time, re, secrets, hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

SCHOOLS_FILE = "schools.csv"
DEPARTMENTS_FILE = "departments.csv"
REPS_FILE = "reps.csv"
SESSIONS_FILE = "sessions.csv"
RECORDS_FILE = "records.csv"
CODES_FILE = "codes.csv"

TOKEN_LIFETIME = 20

SESSION_COLS = ["session_id","school","department","level","title","status","created_at"]
RECORD_COLS = ["session_id","school","department","level","name","matric","time","device_id"]
CODE_COLS = ["session_id","code","created_at"]
REP_COLS = ["username","password","school","department","level"]

LEVELS = ["100","200","300","400","500"]

def load_csv(file, cols):
    if not os.path.exists(file):
        return pd.DataFrame(columns=cols)

    try:
        df = pd.read_csv(file, dtype=str)
        if df.empty and list(df.columns) == []:
            return pd.DataFrame(columns=cols)
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=cols)
        
def save_csv(df, file):
    df.to_csv(file, index=False)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize(txt):
    return re.sub(r"\s+", " ", str(txt).strip()).lower()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def device_id():
    if "device_id" not in st.session_state:
        raw = f"{time.time()}{secrets.token_hex()}"
        st.session_state.device_id = hashlib.sha256(raw.encode()).hexdigest()
    return st.session_state.device_id

def gen_code():
    return f"{secrets.randbelow(10000):04d}"
def write_new_code(session_id):
    codes = load_csv(CODES_FILE, CODE_COLS)
    code = gen_code()
    codes.loc[len(codes)] = [session_id, code, now()]
    save_csv(codes, CODES_FILE)
    return code

def get_latest_code(session_id):
    codes = load_csv(CODES_FILE, CODE_COLS)
    codes = codes[codes["session_id"] == session_id]
    if codes.empty:
        return None
    codes["created_at"] = pd.to_datetime(codes["created_at"])
    return codes.sort_values("created_at").iloc[-1]

def code_valid(session_id, entered):
    latest = get_latest_code(session_id)
    if latest is None:
        return False
    age = (datetime.now() - latest["created_at"]).total_seconds()
    return str(latest["code"]) == str(entered).zfill(4) and age <= TOKEN_LIFETIME

def rep_live_code(session_id):
    latest = get_latest_code(session_id)
    if latest is None:
        return write_new_code(session_id), TOKEN_LIFETIME
    age = (datetime.now() - latest["created_at"]).total_seconds()
    if age >= TOKEN_LIFETIME:
        return write_new_code(session_id), TOKEN_LIFETIME
    return latest["code"], int(TOKEN_LIFETIME - age)
def student_page():
    st.title("ULAS — Student Attendance")

    schools = load_csv(SCHOOLS_FILE, ["name"])
    school = st.selectbox("School", schools["name"])

    depts = load_csv(DEPARTMENTS_FILE, ["school","department"])
    department = st.selectbox(
        "Department",
        depts[depts["school"] == school]["department"]
    )

    level = st.selectbox("Level", LEVELS)

    sessions = load_csv(SESSIONS_FILE, SESSION_COLS)
    active = sessions[
        (sessions["school"] == school) &
        (sessions["department"] == department) &
        (sessions["level"] == level) &
        (sessions["status"] == "Active")
    ]

    if active.empty:
        st.info("No active attendance")
        return

    session = active.iloc[-1]
    sid = session["session_id"]

    code = st.text_input("4-digit code")

    if st.button("Verify Code"):
        if not code_valid(sid, code):
            st.error("Invalid or expired code")
            return
        st.session_state.sid = sid
        st.success("Code accepted")

    if st.session_state.get("sid") != sid:
        return

    name = st.text_input("Full Name")
    matric = st.text_input("Matric Number")

    if st.button("Submit Attendance"):
        records = load_csv(RECORDS_FILE, RECORD_COLS)

        if normalize(name) in records["name"].apply(normalize).values:
            st.error("Name already recorded")
            return
        if matric in records["matric"].values:
            st.error("Matric already used")
            return
        if device_id() in records["device_id"].values:
            st.error("One entry per device")
            return

        records.loc[len(records)] = [
            sid, school, department, level,
            name, matric, now(), device_id()
        ]
        save_csv(records, RECORDS_FILE)
        st.success("Attendance submitted")

def rep_login():
    st.title("Course Rep Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    reps = load_csv(REPS_FILE, REP_COLS)

    if st.button("Login"):
        hashed = hash_password(password)
        rep = reps[
            (reps["username"] == username) &
            (reps["password"] == hashed)
        ]
        if rep.empty:
            st.error("Invalid login")
            return
        st.session_state.rep = rep.iloc[0].to_dict()
        st.rerun()
def rep_dashboard():
    st_autorefresh(interval=1000, key="rep_refresh")

    rep = st.session_state.rep
    school = rep["school"]
    department = rep["department"]
    level = rep["level"]

    st.title("Course Rep Dashboard")
    st.write(f"**{school} / {department} / {level} Level**")

    sessions = load_csv(SESSIONS_FILE, SESSION_COLS)

    if st.button("Start Attendance"):
        sid = str(time.time())
        sessions.loc[len(sessions)] = [
            sid, school, department, level,
            f"{department} {level}", "Active", now()
        ]
        save_csv(sessions, SESSIONS_FILE)
        write_new_code(sid)
        st.rerun()

    my_sessions = sessions[
        (sessions["school"] == school) &
        (sessions["department"] == department) &
        (sessions["level"] == level)
    ]

    if my_sessions.empty:
        return

    sid = st.selectbox("Attendance Sessions", my_sessions["session_id"])
    session = my_sessions[my_sessions["session_id"] == sid].iloc[0]

    if session["status"] == "Active":
        code, remaining = rep_live_code(sid)
        st.markdown(f"## Live Code: `{code}`")
        st.caption(f"Changes in {remaining}s")

        if st.button("End Attendance"):
            sessions.loc[
                sessions["session_id"] == sid,
                "status"
            ] = "Ended"
            save_csv(sessions, SESSIONS_FILE)
            st.success("Attendance ended")
            st.rerun()

    records = load_csv(RECORDS_FILE, RECORD_COLS)
    data = records[records["session_id"] == sid]

    st.dataframe(data[["name","matric","time"]])

    st.download_button(
        "Download CSV",
        data=data[["name","matric","time"]].to_csv(index=False),
        file_name="attendance.csv"
    )

def main():
    page = st.sidebar.selectbox("Page", ["Student","Course Rep"])

    if page == "Student":
        student_page()
    else:
        if "rep" not in st.session_state:
            rep_login()
        else:
            rep_dashboard()

if __name__ == "__main__":
    main()
