import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os
import streamlit.components.v1 as components

# ────────────────────────────────────────────────
#               CONFIGURATION
# ────────────────────────────────────────────────

LECTURE_HALL_LAT       = 5.3834924
LECTURE_HALL_LON       = 6.9991832
ALLOWED_RADIUS_METERS  = 80           # Adjust after real testing (60–120 typical)

# CHANGE THIS BEFORE REAL USE — only the course rep should know it
ADMIN_PASSWORD         = "course_rep_2025_secret"   # ← VERY IMPORTANT: CHANGE THIS!

STUDENTS_FILE   = "students.csv"
ATTENDANCE_FILE = "attendance.csv"

# Haversine formula - distance in meters
def is_in_lecture_hall(lat: float | None, lon: float | None) -> tuple[bool, float | None]:
    if lat is None or lon is None:
        return False, None
    
    R = 6371000  # Earth radius in meters
    dlat = math.radians(lat - LECTURE_HALL_LAT)
    dlon = math.radians(lon - LECTURE_HALL_LON)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(LECTURE_HALL_LAT)) \
        * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance <= ALLOWED_RADIUS_METERS, round(distance, 1)

# ────────────────────────────────────────────────
#               DATA LOAD FUNCTIONS
# ────────────────────────────────────────────────

def load_students():
    if os.path.exists(STUDENTS_FILE):
        return pd.read_csv(STUDENTS_FILE)
    df = pd.DataFrame(columns=["student_id", "name"])
    df.to_csv(STUDENTS_FILE, index=False)
    return df

def load_attendance():
    if os.path.exists(ATTENDANCE_FILE):
        return pd.read_csv(ATTENDANCE_FILE)
    cols = ["student_id", "name", "date", "time", "session", "distance_m"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(ATTENDANCE_FILE, index=False)
    return df

# ────────────────────────────────────────────────
#               SESSION STATE INITIALIZATION
# ────────────────────────────────────────────────

# Defensive initialization - ensures keys exist even on cold start
required_keys = {
    "initialized": False,
    "students_df": load_students(),
    "attendance_df": load_attendance(),
    "attendance_active": False,
    "current_session": None,
    "user_role": None,
    "user_id": None,
}

for key, default in required_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

if not st.session_state["initialized"]:
    st.session_state["initialized"] = True

# Safe shortcuts
students_df   = st.session_state["students_df"]
attendance_df = st.session_state["attendance_df"]

# ────────────────────────────────────────────────
#               SIDEBAR – LOGIN
# ────────────────────────────────────────────────

st.sidebar.title("Attendance System")

if st.session_state["user_role"] is None:
    st.sidebar.subheader("Login")
    user_id_input = st.sidebar.text_input("Student ID / Matric No", key="login_student_id").strip()
    admin_pw_input = st.sidebar.text_input("Password (Course Rep only)", type="password", key="admin_password")

    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("Login as Student"):
        if not user_id_input:
            st.sidebar.error("Please enter your Student ID")
        elif user_id_input in students_df["student_id"].values:
            st.session_state["user_role"] = "student"
            st.session_state["user_id"]   = user_id_input
            st.rerun()
        else:
            st.sidebar.error("Student ID not found. Ask the Course Rep to add you.")

    if col2.button("Login as Course Rep"):
        if admin_pw_input == ADMIN_PASSWORD:
            st.session_state["user_role"] = "admin"
            st.rerun()
        else:
            st.sidebar.error("Incorrect password")

else:
    role_display = "Course Rep (Admin)" if st.session_state["user_role"] == "admin" else "Student"
    id_display = st.session_state["user_id"] or "Admin"
    st.sidebar.markdown(f"**Logged in as** {role_display} ({id_display})")
    
    if st.sidebar.button("Logout"):
        st.session_state.pop("user_role", None)
        st.session_state.pop("user_id", None)
        st.rerun()

# ────────────────────────────────────────────────
#               MAIN CONTENT
# ────────────────────────────────────────────────

st.title("Lecture Attendance – Location Verified")
st.caption(f"Reference location: {LECTURE_HALL_LAT:.6f}, {LECTURE_HALL_LON:.6f}  |  Allowed radius: ±{ALLOWED_RADIUS_METERS} m")

if st.session_state["user_role"] is None:
    st.info("Please log in from the sidebar.")
    st.stop()

# ── ADMIN (COURSE REP) PANEL ────────────────────────────────
if st.session_state["user_role"] == "admin":
    st.subheader("Course Representative Controls")

    with st.expander("Manage Students"):
        new_id = st.text_input("New Student ID", key="admin_new_id")
        new_name = st.text_input("Full Name", key="admin_new_name")
        
        if st.button("Add Student"):
            if new_id.strip() and new_name.strip():
                if new_id in students_df["student_id"].values:
                    st.error("This Student ID already exists")
                else:
                    new_row = pd.DataFrame({"student_id": [new_id], "name": [new_name]})
                    students_df = pd.concat([students_df, new_row], ignore_index=True)
                    students_df.to_csv(STUDENTS_FILE, index=False)
                    st.session_state["students_df"] = students_df
                    st.success(f"Added {new_name} ({new_id})")
                    st.rerun()
            else:
                st.error("Both fields are required")

        if not students_df.empty:
            st.dataframe(students_df.style.hide(axis="index"), use_container_width=True)

    st.subheader("Attendance Session Control")
    
    if not st.session_state["attendance_active"]:
        default_name = datetime.now().strftime("%Y-%m-%d   %H:%M   Lecture")
        session_name = st.text_input("Session / Course & Date", value=default_name)
        
        if st.button("Start Attendance Session"):
            if session_name.strip():
                st.session_state["attendance_active"] = True
                st.session_state["current_session"] = session_name.strip()
                st.success(f"Session started: **{session_name}**")
                st.rerun()
            else:
                st.error("Please enter a session name")
    else:
        st.success(f"**ACTIVE SESSION:** {st.session_state['current_session']}")
        if st.button("End Session"):
            st.session_state["attendance_active"] = False
            st.session_state["current_session"] = None
            st.success("Session has been closed.")
            st.rerun()

    if st.button("View All Attendance Records"):
        if attendance_df.empty:
            st.info("No attendance records yet.")
        else:
            st.dataframe(
                attendance_df.sort_values(by="date", ascending=False),
                use_container_width=True,
                hide_index=True
            )

# ── STUDENT PANEL ───────────────────────────────────────────
elif st.session_state["user_role"] == "student":
    st.subheader("Mark Your Attendance")

    if not st.session_state["attendance_active"]:
        st.warning("No active attendance session right now. Please wait for the Course Rep to start one.")
    else:
        already_marked = attendance_df[
            (attendance_df["student_id"] == st.session_state["user_id"]) &
            (attendance_df["session"] == st.session_state["current_session"])
        ].shape[0] > 0

        if already_marked:
            st.success("You have **already marked** attendance for this session.")
        else:
            st.write("**Share your location** to confirm you are in the lecture hall:")

            # JavaScript geolocation component
            geo_component = """
            <div id="geo-status" style="margin: 1em 0; font-weight: bold;">Waiting for location...</div>
            <button id="geo-button" onclick="getLocation()">Get Location & Mark</button>

            <script>
            function getLocation() {
                const status = document.getElementById("geo-status");
                const btn = document.getElementById("geo-button");
                btn.disabled = true;
                btn.innerText = "Requesting...";

                if (!navigator.geolocation) {
                    status.innerHTML = "Geolocation is not supported by this browser.";
                    btn.disabled = false;
                    btn.innerText = "Retry";
                    return;
                }

                status.innerHTML = "Getting location... (please allow permission)";

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude.toFixed(6);
                        const lon = position.coords.longitude.toFixed(6);
                        const acc = Math.round(position.coords.accuracy);

                        status.innerHTML = `Location received!<br>Lat: ${lat}<br>Lon: \( {lon}<br>Accuracy: ± \){acc} m`;

                        // Pass data to Streamlit via query params
                        const params = new URLSearchParams(window.location.search);
                        params.set('lat', lat);
                        params.set('lon', lon);
                        params.set('acc', acc);
                        window.location.search = params.toString();
                    },
                    (error) => {
                        let msg = "Error: ";
                        switch(error.code) {
                            case error.PERMISSION_DENIED:  msg += "Permission denied"; break;
                            case error.POSITION_UNAVAILABLE: msg += "Position unavailable"; break;
                            case error.TIMEOUT:            msg += "Request timed out"; break;
                            default:                       msg += "Unknown error";
                        }
                        status.innerHTML = msg;
                        btn.disabled = false;
                        btn.innerText = "Retry";
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 12000,
                        maximumAge: 0
                    }
                );
            }

            // Auto start (comment out if you prefer button only)
            window.addEventListener('load', () => setTimeout(getLocation, 800));
            </script>
            """

            components.html(geo_component, height=220)

            # Read location from query params
            params = st.query_params
            lat_str = params.get("lat", [None])[0]
            lon_str = params.get("lon", [None])[0]
            acc_str = params.get("acc", [None])[0]

            if lat_str and lon_str:
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    acc = float(acc_str) if acc_str else 999.0

                    if acc > 120:
                        st.error(f"Location accuracy too low (±{acc} m). Try again near a window or outside.")
                    else:
                        inside, dist = is_in_lecture_hall(lat, lon)

                        if inside:
                            name_row = students_df[students_df["student_id"] == st.session_state["user_id"]]
                            name = name_row["name"].iloc[0] if not name_row.empty else "Unknown"

                            now = datetime.now()
                            new_record = pd.DataFrame([{
                                "student_id": st.session_state["user_id"],
                                "name": name,
                                "date": now.strftime("%Y-%m-%d"),
                                "time": now.strftime("%H:%M:%S"),
                                "session": st.session_state["current_session"],
                                "distance_m": dist
                            }])

                            attendance_df = pd.concat([attendance_df, new_record], ignore_index=True)
                            attendance_df.to_csv(ATTENDANCE_FILE, index=False)
                            st.session_state["attendance_df"] = attendance_df

                            st.success(f"**Attendance marked successfully!**  ≈ {dist} m from center (accuracy ±{acc} m)")
                        else:
                            st.error(f"You appear to be outside the lecture hall area (≈ {dist} m away).")
                except Exception as e:
                    st.error("Error processing location. Please try again.")

            # Optional: clear params after processing (prevents duplicate marking on refresh)
            if "lat" in params:
                st.query_params.clear()

# ── FOOTER ──────────────────────────────────────────────────
st.markdown("---")
st.caption("Location-verified attendance system • Requires browser location permission")
