import streamlit as st
import pandas as pd
from datetime import datetime
import random
import string
import os
import json
import hashlib

# ────────────────────────────────────────────────
#               CONFIGURATION
# ────────────────────────────────────────────────

SCHOOLS_DEPTS = {
    "SAAT (Agriculture & Agric Tech)": [
        "Agricultural Economics", "Agricultural Extension", "Animal Science and Technology",
        "Crop Science and Technology", "Fisheries and Aquaculture Technology",
        "Forestry and Wildlife Technology", "Soil Science and Technology"
    ],
    "SEET (Engineering & Eng Tech)": [
        "Agricultural and Bioresources Engineering", "Biomedical Engineering", "Chemical Engineering",
        "Civil Engineering", "Electrical and Electronics Engineering", "Food Science and Technology",
        "Materials and Metallurgical Engineering", "Mechanical Engineering", "Mechatronic Engineering",
        "Petroleum Engineering", "Polymer and Textile Engineering"
    ],
    "SOES (Environmental Tech)": [
        "Architecture", "Building Technology", "Environmental Technology", "Quantity Surveying",
        "Surveying and Geoinformatics", "Urban and Regional Planning"
    ],
    "SOHT (Health Tech)": [
        "Biomedical Technology", "Dental Technology", "Environmental Health Science", "Optometry",
        "Prosthetics and Orthotics", "Public Health Technology"
    ],
    "SICT (Info & Comm Tech)": [
        "Computer Science", "Cyber Security Science", "Information Technology", "Software Engineering"
    ],
    "SMAT (Management Tech)": [
        "Financial Management Technology", "Information Management Technology",
        "Maritime Management Technology", "Project Management Technology", "Transport Management Technology"
    ],
    "SOPS (Physical Sciences)": [
        "Chemistry", "Geology", "Mathematics", "Physics", "Statistics"
    ],
    "SOBS (Biological Sciences)": [
        "Biochemistry", "Biology", "Biotechnology", "Microbiology", "Forensic Science"
    ],
    "SBMS (Basic Medical Sciences)": [
        "Anatomy", "Physiology"
    ],
}

LEVELS = ["100 Level", "200 Level", "300 Level", "400 Level", "500 Level"]

# CHANGE THESE TWO BEFORE USING!
SETUP_SECRET = "futo_setup_2026_admin"           # Secret to access rep creation mode
INITIAL_ADMIN_PASSWORD = "change_me_12345"       # Use this only the first time

STUDENTS_FILE    = "students.csv"
ATTENDANCE_FILE  = "attendance.csv"
CODES_FILE       = "attendance_codes.json"
REPS_FILE        = "course_reps.json"   # { "school-dept-level": "hashed_password" }
# ────────────────────────────────────────────────
#               HELPER FUNCTIONS
# ────────────────────────────────────────────────

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def generate_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

def load_reps() -> dict:
    if os.path.exists(REPS_FILE):
        with open(REPS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_reps(data: dict):
    with open(REPS_FILE, "w") as f:
        json.dump(data, f)

def load_codes() -> dict:
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_codes(data: dict):
    with open(CODES_FILE, "w") as f:
        json.dump(data, f)
# ────────────────────────────────────────────────
#               SESSION STATE INITIALIZATION
# ────────────────────────────────────────────────

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.students_df = (
        pd.read_csv(STUDENTS_FILE)
        if os.path.exists(STUDENTS_FILE)
        else pd.DataFrame(columns=["student_id", "name", "school", "dept", "level"])
    )
    st.session_state.attendance_df = (
        pd.read_csv(ATTENDANCE_FILE)
        if os.path.exists(ATTENDANCE_FILE)
        else pd.DataFrame(columns=["student_id", "name", "school", "dept", "level", "date", "time", "session"])
    )
    st.session_state.codes = load_codes()
    st.session_state.reps = load_reps()
    st.session_state.user_role = None
    st.session_state.user_data = {}

students_df   = st.session_state.students_df
attendance_df = st.session_state.attendance_df
codes         = st.session_state.codes
reps          = st.session_state.reps
# ────────────────────────────────────────────────
#               SIDEBAR – LOGIN & SETUP
# ────────────────────────────────────────────────

st.sidebar.title("FUTO Attendance System")

# Hidden setup mode for creating course reps
setup_mode = st.sidebar.checkbox("Admin Setup (Course Rep Creation)", value=False)
if setup_mode:
    secret_input = st.sidebar.text_input("Setup Secret Key", type="password")
    if secret_input == SETUP_SECRET:
        st.sidebar.success("Setup mode enabled")
        s_setup = st.sidebar.selectbox("School", list(SCHOOLS_DEPTS.keys()), key="s_setup")
        d_setup = st.sidebar.selectbox("Department", SCHOOLS_DEPTS[s_setup], key="d_setup")
        l_setup = st.sidebar.selectbox("Level", LEVELS, key="l_setup")
        new_password = st.sidebar.text_input("New Course Rep Password", type="password", key="new_pw")
        rep_key = f"{s_setup}-{d_setup}-{l_setup}"

        if st.sidebar.button("Create / Update Course Rep"):
            if new_password.strip():
                reps[rep_key] = hash_pw(new_password.strip())
                save_reps(reps)
                st.session_state.reps = reps
                st.sidebar.success(f"Course Rep set for {rep_key}")
            else:
                st.sidebar.error("Enter a password")
    else:
        if secret_input:
            st.sidebar.error("Incorrect secret key")

# Normal login
role = st.sidebar.radio("Login As", ["Student", "Course Rep"])

school = st.sidebar.selectbox("School", list(SCHOOLS_DEPTS.keys()))
dept   = st.sidebar.selectbox("Department", SCHOOLS_DEPTS[school])
level  = st.sidebar.selectbox("Level", LEVELS)

key_prefix = f"{school}-{dept}-{level}"

if role == "Student":
    student_id = st.sidebar.text_input("Matric Number").strip().upper()
    if st.sidebar.button("Login / Register"):
        if not student_id:
            st.sidebar.error("Enter Matric Number")
        else:
            match = students_df[
                (students_df["student_id"] == student_id) &
                (students_df["school"] == school) &
                (students_df["dept"] == dept) &
                (students_df["level"] == level)
            ]
            if not match.empty:
                st.session_state.user_role = "student"
                st.session_state.user_data = {
                    "school": school, "dept": dept, "level": level,
                    "student_id": student_id, "name": match["name"].iloc[0]
                }
                st.rerun()
            else:
                name = st.sidebar.text_input("Your Full Name (first time)")
                if name and st.sidebar.button("Register"):
                    new_row = pd.DataFrame({
                        "student_id": [student_id], "name": [name],
                        "school": [school], "dept": [dept], "level": [level]
                    })
                    st.session_state.students_df = pd.concat([students_df, new_row], ignore_index=True)
                    st.session_state.students_df.to_csv(STUDENTS_FILE, index=False)
                    st.session_state.user_role = "student"
                    st.session_state.user_data = {
                        "school": school, "dept": dept, "level": level,
                        "student_id": student_id, "name": name
                    }
                    st.success("Registered!")
                    st.rerun()

else:  # Course Rep
    password_input = st.sidebar.text_input("Your Password", type="password")
    if st.sidebar.button("Login as Course Rep"):
        rep_key = key_prefix
        if rep_key in reps and hash_pw(password_input) == reps[rep_key]:
            st.session_state.user_role = "admin"
            st.session_state.user_data = {
                "school": school, "dept": dept, "level": level, "rep_key": rep_key
            }
            st.rerun()
        else:
            st.sidebar.error("Incorrect password or no account for this level")

# Show current login status
if st.session_state.user_role is not None:
    data = st.session_state.user_data
    role_text = "Course Rep" if st.session_state.user_role == "admin" else "Student"
    st.sidebar.markdown(
        f"**Logged in as {role_text}**  \n"
        f"{data.get('school')} → {data.get('dept')} → {data.get('level')}"
    )
    if st.sidebar.button("Logout"):
        st.session_state.user_role = None
        st.session_state.user_data = {}
        st.rerun()
# ────────────────────────────────────────────────
#               MAIN CONTENT
# ────────────────────────────────────────────────

st.title("FUTO Departmental Attendance System")
st.caption("One-time unique codes • Each level has its own Course Rep")

if st.session_state.user_role is None:
    st.info("Please log in using the sidebar.")
    st.stop()

session_key = key_prefix

if st.session_state.user_role == "admin":
    st.subheader("Course Rep Dashboard")

    current_session_name = st.session_state.get("current_session", {}).get(session_key)

    if current_session_name is None:
        session_name_input = st.text_input("Session / Course & Date")
        if st.button("Start Attendance Session"):
            if session_name_input.strip():
                dept_students = students_df[
                    (students_df["school"] == data["school"]) &
                    (students_df["dept"] == data["dept"]) &
                    (students_df["level"] == data["level"])
                ]
                if dept_students.empty:
                    st.warning("No students registered in this level yet.")
                else:
                    new_codes_dict = {}
                    for _, row in dept_students.iterrows():
                        new_codes_dict[row["student_id"]] = generate_code()

                    codes[session_key] = {
                        "session_name": session_name_input.strip(),
                        "codes": new_codes_dict
                    }
                    save_codes(codes)
                    st.session_state.codes = codes
                    st.session_state.current_session = {session_key: session_name_input.strip()}
                    st.success(f"Session started. {len(new_codes_dict)} codes generated.")
                    st.rerun()
            else:
                st.error("Please enter session name")
    else:
        st.success(f"**Active Session:** {current_session_name}")
        current_codes = codes.get(session_key, {}).get("codes", {})

        if current_codes:
            code_list = [{"Matric Number": sid, "Code": code} for sid, code in current_codes.items()]
            st.dataframe(pd.DataFrame(code_list).sort_values("Matric Number"), use_container_width=True, hide_index=True)

            txt_content = "\n".join([f"{sid}: {code}" for sid, code in current_codes.items()])
            st.download_button(
                label="Download all codes (TXT)",
                data=txt_content,
                file_name=f"codes_{session_key.replace(' ', '_')}.txt",
                mime="text/plain"
            )

        if st.button("End Session & Delete Codes"):
            if session_key in codes:
                del codes[session_key]
                save_codes(codes)
                st.session_state.codes = codes
            if "current_session" in st.session_state and session_key in st.session_state.current_session:
                del st.session_state.current_session[session_key]
            st.success("Session closed. Codes removed.")
            st.rerun()

    # Attendance records for this level
    level_records = attendance_df[
        (attendance_df["school"] == data["school"]) &
        (attendance_df["dept"] == data["dept"]) &
        (attendance_df["level"] == data["level"])
    ]
    if st.button("Show Attendance Records"):
        if level_records.empty:
            st.info("No attendance recorded yet for this level.")
        else:
            st.dataframe(level_records.sort_values("date", ascending=False), use_container_width=True)

elif st.session_state.user_role == "student":
    st.subheader("Mark Your Attendance")

    current_session_name = st.session_state.get("current_session", {}).get(session_key)

    if current_session_name is None:
        st.warning("No active attendance session for your level right now.")
    else:
        already_marked = attendance_df[
            (attendance_df["student_id"] == data["student_id"]) &
            (attendance_df["session"] == current_session_name) &
            (attendance_df["school"] == data["school"]) &
            (attendance_df["dept"] == data["dept"]) &
            (attendance_df["level"] == data["level"])
        ].shape[0] > 0

        if already_marked:
            st.success("You have already been marked present for this session.")
        else:
            user_code = st.text_input("Enter the unique code from your Course Rep", max_chars=6).strip().upper()

            if st.button("Submit Code"):
                if not user_code:
                    st.error("Please enter the code")
                else:
                    session_data = codes.get(session_key, {})
                    session_codes = session_data.get("codes", {})
                    assigned_code = session_codes.get(data["student_id"])

                    if assigned_code and user_code == assigned_code:
                        now = datetime.now()
                        record = {
                            "student_id": data["student_id"],
                            "name": data["name"],
                            "school": data["school"],
                            "dept": data["dept"],
                            "level": data["level"],
                            "date": now.strftime("%Y-%m-%d"),
                            "time": now.strftime("%H:%M:%S"),
                            "session": current_session_name
                        }
                        new_record_df = pd.DataFrame([record])
                        st.session_state.attendance_df = pd.concat(
                            [attendance_df, new_record_df], ignore_index=True
                        )
                        st.session_state.attendance_df.to_csv(ATTENDANCE_FILE, index=False)

                        # Invalidate used code
                        del session_codes[data["student_id"]]
                        if not session_codes:
                            if session_key in codes:
                                del codes[session_key]
                        else:
                            codes[session_key]["codes"] = session_codes
                        save_codes(codes)
                        st.session_state.codes = codes

                        st.success("Attendance successfully marked!")
                        st.rerun()
                    else:
                        st.error("Invalid or already used code. Please check with your Course Rep.")

# Footer
st.markdown("---")
st.caption(
    "FUTO Attendance System • Per-level Course Rep login • "
    "Unique one-time codes • Contact your level Course Rep for password or code"
            )
