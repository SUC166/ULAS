import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation
import math
import os

# ────────────────────────────────────────────────
#               CONFIGURATION
# ────────────────────────────────────────────────

LECTURE_HALL_LAT       = 5.3834924
LECTURE_HALL_LON       = 6.9991832
ALLOWED_RADIUS_METERS  = 80           # Adjust after real testing (60–120 typical)

# CHANGE THIS BEFORE DEPLOYING — only course rep should know it
ADMIN_PASSWORD         = "course_rep_2025_secret"   # ← IMPORTANT: CHANGE THIS!

STUDENTS_FILE   = "students.csv"
ATTENDANCE_FILE = "attendance.csv"

# Simple haversine formula (distance in meters)
def is_in_lecture_hall(lat: float | None, lon: float | None) -> tuple[bool, float | None]:
    if lat is None or lon is None:
        return False, None
    
    R = 6371000  # Earth radius (m)
    dlat = math.radians(lat - LECTURE_HALL_LAT)
    dlon = math.radians(lon - LECTURE_HALL_LON)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(LECTURE_HALL_LAT)) \
        * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance <= ALLOWED_RADIUS_METERS, round(distance)

# ────────────────────────────────────────────────
#               DATA INITIALIZATION
# ────────────────────────────────────────────────

@st.cache_data(ttl="10min")  # small cache helps on cloud
def load_students():
    if os.path.exists(STUDENTS_FILE):
        return pd.read_csv(STUDENTS_FILE)
    else:
        df = pd.DataFrame(columns=["student_id", "name"])
        df.to_csv(STUDENTS_FILE, index=False)
        return df

@st.cache_data(ttl="30s")
def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        return pd.read_csv(ATTENDANCE_FILE)
    else:
        cols = ["student_id", "name", "date", "time", "session", "distance_m"]
        df = pd.DataFrame(columns=cols)
        df.to_csv(ATTENDANCE_FILE, index=False)
        return df

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.students_df    = load_students()
    st.session_state.attendance_df  = load_attendance()
    st.session_state.attendance_active = False
    st.session_state.current_session   = None
    st.session_state.user_role         = None
    st.session_state.user_id           = None

# Shortcuts
students_df   = st.session_state.students_df
attendance_df = st.session_state.attendance_df

# ────────────────────────────────────────────────
#               SIDEBAR – LOGIN
# ────────────────────────────────────────────────

st.sidebar.title("Attendance System")

if st.session_state.user_role is None:
    st.sidebar.subheader("Login")
    user_id = st.sidebar.text_input("Student ID / Matric No", key="login_id").strip()
    admin_pw = st.sidebar.text_input("Password (Course Rep only)", type="password", key="admin_pw")

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Login as Student"):
        if not user_id:
            st.sidebar.error("Enter Student ID")
        elif user_id in students_df["student_id"].values:
            st.session_state.user_role = "student"
            st.session_state.user_id   = user_id
            st.rerun()
        else:
            st.sidebar.error("ID not found. Ask Course Rep to add you.")

    if col2.button("Login as Course Rep"):
        if admin_pw == ADMIN_PASSWORD:
            st.session_state.user_role = "admin"
            st.rerun()
        else:
            st.sidebar.error("Incorrect password")

else:
    role_text = "Course Rep (Admin)" if st.session_state.user_role == "admin" else "Student"
    uid_text = st.session_state.user_id or "Admin"
    st.sidebar.markdown(f"**Logged in as** {role_text} ({uid_text})")
    if st.sidebar.button("Logout"):
        for k in ["user_role", "user_id"]:
            st.session_state.pop(k, None)
        st.rerun()

# ────────────────────────────────────────────────
#               MAIN PAGE
# ────────────────────────────────────────────────

st.title("Lecture Attendance – Location Verified")

st.caption(f"Hall coordinates: {LECTURE_HALL_LAT:.6f}, {LECTURE_HALL_LON:.6f}  |  Radius: ±{ALLOWED_RADIUS_METERS} m")

if st.session_state.user_role is None:
    st.info("Please log in using the sidebar.")
    st.stop()

# ── ADMIN PANEL ───────────────────────────────────────
if st.session_state.user_role == "admin":
    st.subheader("Course Rep Controls")

    with st.expander("Manage Students", expanded=False):
        new_id = st.text_input("New Student ID", key="new_id")
        new_name = st.text_input("Full Name", key="new_name")
        if st.button("Add Student"):
            if new_id and new_name:
                if new_id in students_df["student_id"].values:
                    st.error("This ID already exists")
                else:
                    new_row = pd.DataFrame({"student_id": [new_id], "name": [new_name]})
                    students_df = pd.concat([students_df, new_row], ignore_index=True)
                    students_df.to_csv(STUDENTS_FILE, index=False)
                    st.session_state.students_df = students_df
                    st.success(f"Added {new_name} ({new_id})")
                    st.rerun()
            else:
                st.error("Fill both fields")

        if not students_df.empty:
            st.dataframe(students_df.style.hide(axis="index"), use_container_width=True)

    # Session control
    st.subheader("Attendance Session")
    if not st.session_state.attendance_active:
        default_session = datetime.now().strftime("%Y-%m-%d  %H:%M  Lecture")
        session_name = st.text_input("Session name / Course & Date", value=default_session)
        if st.button("Start Attendance"):
            if session_name.strip():
                st.session_state.attendance_active = True
                st.session_state.current_session = session_name.strip()
                st.success(f"Session started → {session_name}")
                st.rerun()
            else:
                st.error("Enter a session name")
    else:
        st.success(f"**ACTIVE SESSION:** {st.session_state.current_session}")
        if st.button("End Session & Close Marking"):
            st.session_state.attendance_active = False
            st.session_state.current_session = None
            st.success("Session closed.")
            st.rerun()

    if st.button("Show All Attendance Records"):
        if attendance_df.empty:
            st.info("No records yet.")
        else:
            st.dataframe(
                attendance_df.sort_values("date", ascending=False),
                use_container_width=True,
                hide_index=True
            )

# ── STUDENT PANEL ─────────────────────────────────────
elif st.session_state.user_role == "student":
    st.subheader("Mark Your Attendance")

    if not st.session_state.attendance_active:
        st.warning("No active session. Wait for the Course Rep to start attendance.")
    else:
        # Already marked check
        already = attendance_df[
            (attendance_df["student_id"] == st.session_state.user_id) &
            (attendance_df["session"] == st.session_state.current_session)
        ].shape[0] > 0

        if already:
            st.success("You have **already marked** attendance for this session.")
        else:
            st.write("Share your location to confirm you're in the lecture hall:")

            location = streamlit_geolocation(key=f"loc_{st.session_state.user_id}")

            if location and "latitude" in location and location["latitude"] is not None:
                lat = location["latitude"]
                lon = location["longitude"]
                inside, dist = is_in_lecture_hall(lat, lon)

                if inside:
                    name = students_df.loc[students_df["student_id"] == st.session_state.user_id, "name"].iloc[0]
                    now = datetime.now()
                    record = {
                        "student_id": st.session_state.user_id,
                        "name": name,
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M:%S"),
                        "session": st.session_state.current_session,
                        "distance_m": dist
                    }
                    new_df = pd.DataFrame([record])
                    attendance_df = pd.concat([attendance_df, new_df], ignore_index=True)
                    attendance_df.to_csv(ATTENDANCE_FILE, index=False)
                    st.session_state.attendance_df = attendance_df

                    st.success(f"Attendance recorded! (≈ {dist} m from center)")
                else:
                    st.error(f"Too far from lecture hall (≈ {dist} m). You must be inside the room.")
            elif location and location.get("error"):
                st.error("Location permission denied or failed. Please allow location access.")
            else:
                st.info("Waiting for location… (browser will ask for permission)")

# Footer
st.markdown("---")
st.caption("Location-based attendance system • GPS within lecture hall required")
