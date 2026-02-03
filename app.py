import streamlit as st
import pandas as pd
import os, re, time, secrets, hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

TOKEN_LIFETIME = 20

SESSIONS_FILE = "sessions.csv"
RECORDS_FILE = "records.csv"
CODES_FILE = "codes.csv"
SCHOOLS_FILE = "schools.csv"
DEPARTMENTS_FILE = "departments.csv"
REPS_FILE = "reps.csv"

SESSION_COLS = ["session_id","school","department","level","title","status","created_at"]
RECORD_COLS = ["session_id","school","department","level","name","matric","time","device_id"]
CODE_COLS = ["session_id","code","created_at"]
REP_COLS = ["username","password","school","department","level"]

LEVELS = ["100","200","300","400","500"]

def load_csv(file, cols):
    return pd.read_csv(file, dtype=str) if os.path.exists(file) else pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize(txt):
    return re.sub(r"\s+", " ", str(txt).strip()).lower()

def device_id():
    if "device_id" not in st.session_state:
        raw = f"{time.time()}{secrets.token_hex()}"
        st.session_state.device_id = hashlib.sha256(raw.encode()).hexdigest()
    return st.session_state.device_id

def gen_code():
    return f"{secrets.randbelow(10000):04d}"
# ---------- INIT DEFAULT DATA ----------
if not os.path.exists(SCHOOLS_FILE):
    save_csv(pd.DataFrame({"name":["SEET","SICT","SOBS","SMAT"]}), SCHOOLS_FILE)

if not os.path.exists(DEPARTMENTS_FILE):
    save_csv(pd.DataFrame({
        "school":["SICT","SICT","SEET","SOBS"],
        "department":["Computer Science","Software Engineering","Mechanical Engineering","Microbiology"]
    }), DEPARTMENTS_FILE)

if not os.path.exists(REPS_FILE):
    save_csv(pd.DataFrame([
        ["rep1","pass123","SICT","Computer Science","300"]
    ], columns=REP_COLS), REPS_FILE)

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

def code_valid(session_id, entered_code):
    latest = get_latest_code(session_id)
    if latest is None:
        return False
    age = (datetime.now() - latest["created_at"]).total_seconds()
    return str(latest["code"]) == str(entered_code).zfill(4) and age <= TOKEN_LIFETIME

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
    school = st.selectbox("Select School", schools["name"])

    depts = load_csv(DEPARTMENTS_FILE, ["school","department"])
    dept_list = depts[depts["school"] == school]["department"]
    department = st.selectbox("Select Department", dept_list)

    level = st.selectbox("Select Level", LEVELS)

    sessions = load_csv(SESSIONS_FILE, SESSION_COLS)
    active = sessions[
        (sessions["school"] == school) &
        (sessions["department"] == department) &
        (sessions["level"] == level) &
        (sessions["status"] == "Active")
    ]

    if active.empty:
        st.info("No active attendance for your class.")
        return

    session = active.iloc[-1]
    sid = session["session_id"]

    entered = st.text_input("Enter Live Code")

    if st.button("Continue"):
        if not code_valid(sid, entered):
            st.error("Invalid or expired code")
            return
        st.session_state.sid = sid
        st.success("Code accepted")

    if "sid" not in st.session_state or st.session_state.sid != sid:
        return

    name = st.text_input("Full Name")
    matric = st.text_input("Matric Number (11 digits)")

    if st.button("Submit Attendance"):
        records = load_csv(RECORDS_FILE, RECORD_COLS)

        if normalize(name) in records["name"].apply(normalize).values:
            st.error("Duplicate name")
            return

        if matric in records["matric"].values:
            st.error("Matric already used")
            return

        dev = device_id()
        if dev in records["device_id"].values:
            st.error("One entry per device")
            return

        records.loc[len(records)] = [
            sid, school, department, level, name, matric, now(), dev
        ]

        save_csv(records, RECORDS_FILE)
        st.success("Attendance recorded")
def rep_dashboard():
    st_autorefresh(interval=1000, key="refresh")
    st.title("ULAS — Course Rep Dashboard")

    reps = load_csv(REPS_FILE, REP_COLS)
    rep = reps[reps["username"] == st.session_state.rep_user].iloc[0]

    school = rep["school"]
    department = rep["department"]
    level = rep["level"]

    st.write(f"**{school} — {department} — Level {level}**")

    if st.button("Start Attendance"):
        sessions = load_csv(SESSIONS_FILE, SESSION_COLS)
        sid = str(time.time())
        title = f"{department} {level} — {now()}"

        sessions.loc[len(sessions)] = [
            sid, school, department, level, title, "Active", now()
        ]

        save_csv(sessions, SESSIONS_FILE)
        write_new_code(sid)
        st.rerun()

    sessions = load_csv(SESSIONS_FILE, SESSION_COLS)
    data_sessions = sessions[
        (sessions["school"] == school) &
        (sessions["department"] == department) &
        (sessions["level"] == level)
    ]

    if data_sessions.empty:
        return

    sid = st.selectbox("Select Session", data_sessions["session_id"])
    session = data_sessions[data_sessions["session_id"] == sid].iloc[0]

    records = load_csv(RECORDS_FILE, RECORD_COLS)
    data = records[records["session_id"] == sid]

    if session["status"] == "Active":
        code, remaining = rep_live_code(sid)
        st.markdown(f"## Live Code: `{code}`")
        st.caption(f"Changes in {remaining}s")

        if st.button("🛑 END ATTENDANCE"):
            sessions.loc[sessions["session_id"] == sid, "status"] = "Ended"
            save_csv(sessions, SESSIONS_FILE)
            st.rerun()

    st.subheader("Attendance Records")
    st.dataframe(data[["name","matric","time"]])

    st.download_button(
        "Download CSV",
        data=data[["name","matric","time"]].to_csv(index=False),
        file_name=f"{session['title']}.csv"
    )

def rep_login():
    st.title("Course Rep Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    reps = load_csv(REPS_FILE, REP_COLS)

    if st.button("Login"):
        match = reps[(reps["username"] == u) & (reps["password"] == p)]
        if match.empty:
            st.error("Invalid login")
        else:
            st.session_state.rep_user = u
            st.rerun()

def main():
    page = st.sidebar.selectbox("Page", ["Student", "Course Rep"])

    if page == "Student":
        student_page()
    else:
        if "rep_user" not in st.session_state:
            rep_login()
        else:
            rep_dashboard()

if __name__ == "__main__":
    main()
