# app.py
import streamlit as st
import random
import pandas as pd
import json
import requests
import base64
from datetime import datetime, timedelta
import pytz
import uuid

# ----------------- STREAMLIT SECRETS -----------------
GITHUB_PAT = st.secrets["GITHUB_PAT"]
DATA_REPO = st.secrets["DATA_REPO"]
DATA_OWNER = st.secrets["DATA_OWNER"]
LAVA_REPO = st.secrets["LAVA_REPO"]
LAVA_OWNER = st.secrets["LAVA_OWNER"]

# ----------------- FUTO STRUCTURE -----------------
# Each department mapped to its levels
SCHOOL_STRUCTURE = {
    "SAAT": {
        "Agribusiness": [100,200,300,400,500],
        "Agricultural Economics": [100,200,300,400,500],
        "Agricultural Extension": [100,200,300,400,500],
        "Animal Science and Technology": [100,200,300,400,500],
        "Crop Science and Technology": [100,200,300,400,500],
        "Fisheries and Aquaculture Technology": [100,200,300,400,500],
        "Forestry and Wildlife Technology": [100,200,300,400,500],
        "Soil Science and Technology": [100,200,300,400,500]
    },
    "SBMS": {
        "Human Anatomy": [100,200,300,400],
        "Human Physiology": [100,200,300,400]
    },
    "SOBS": {
        "Biochemistry": [100,200,300,400,500],
        "Biology": [100,200,300,400,500],
        "Biotechnology": [100,200,300,400,500],
        "Microbiology": [100,200,300,400,500],
        "Forensic Science": [100,200,300,400,500]
    },
    "SEET": {
        "Agricultural and Bioresources Engineering":[100,200,300,400,500],
        "Biomedical Engineering":[100,200,300,400,500],
        "Chemical Engineering":[100,200,300,400,500],
        "Civil Engineering":[100,200,300,400,500],
        "Food Science and Technology":[100,200,300,400,500],
        "Material and Metallurgical Engineering":[100,200,300,400,500],
        "Mechanical Engineering":[100,200,300,400,500],
        "Petroleum Engineering":[100,200,300,400,500],
        "Polymer and Textile Engineering":[100,200,300,400,500]
    },
    "SESET": {
        "Computer Engineering":[100,200,300,400,500],
        "Electrical (Power Systems) Engineering":[100,200,300,400,500],
        "Electronics Engineering":[100,200,300,400,500],
        "Mechatronics Engineering":[100,200,300,400,500],
        "Telecommunications Engineering":[100,200,300,400,500],
        "Electrical and Electronic Engineering":[100,200,300,400,500]
    },
    "SOES": {
        "Architecture":[100,200,300,400,500,600],
        "Building Technology":[100,200,300,400,500],
        "Environmental Management":[100,200,300,400,500],
        "Quantity Surveying":[100,200,300,400,500],
        "Surveying and Geoinformatics":[100,200,300,400,500],
        "Urban and Regional Planning":[100,200,300,400,500],
        "Environmental Management and Evaluation":[100,200,300,400,500]
    },
    "SOHT": {
        "Dental Technology":[100,200,300,400,500],
        "Environmental Health Science":[100,200,300,400,500],
        "Optometry":[100,200,300,400,500,600],
        "Prosthetics and Orthotics":[100,200,300,400,500],
        "Public Health Technology":[100,200,300,400,500]
    },
    "SICT": {
        "Computer Science":[100,200,300,400,500],
        "Cyber Security":[100,200,300,400,500],
        "Information Technology":[100,200,300,400,500],
        "Software Engineering":[100,200,300,400,500]
    },
    "SLIT": {
        "Entrepreneurship and Innovation":[100,200,300,400,500],
        "Logistics and Transport Technology":[100,200,300,400,500],
        "Maritime Technology and Logistics":[100,200,300,400,500],
        "Supply Chain Management":[100,200,300,400,500],
        "Project Management Technology":[100,200,300,400,500]
    },
    "SOPS": {
        "Chemistry":[100,200,300,400,500],
        "Geology":[100,200,300,400,500],
        "Mathematics":[100,200,300,400,500],
        "Physics":[100,200,300,400,500],
        "Science Laboratory Technology":[100,200,300,400,500],
        "Statistics":[100,200,300,400,500]
    },
    "CESPESS": {
        "Procurement Management Department":[100,200,300,400],
        "Sustainable Social Development Department":[100,200,300,400],
        "Sustainable Environmental Studies Department":[100,200,300,400]
    }
}

# ----------------- TIMEZONE -----------------
FUTO_TZ = pytz.timezone("Africa/Lagos")

# ----------------- HELPER FUNCTIONS -----------------
def gh_get_file(owner, repo, path):
    """Get file content from GitHub"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_PAT}"})
    if r.status_code == 200:
        content = r.json()
        data = base64.b64decode(content['content']).decode()
        return data
    return None

def gh_put_file(owner, repo, path, content, message):
    """Push file to GitHub"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    existing = requests.get(url, headers={"Authorization": f"token {GITHUB_PAT}"})
    if existing.status_code == 200:
        sha = existing.json()["sha"]
    else:
        sha = None
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha
    }
    r = requests.put(url, json=data, headers={"Authorization": f"token {GITHUB_PAT}"})
    return r.status_code in [200,201]

def generate_token():
    return str(random.randint(1000,9999))

def get_current_time():
    return datetime.now(FUTO_TZ).strftime("%Y-%m-%d %H:%M:%S")

def load_json_from_repo(path):
    content = gh_get_file(DATA_OWNER, DATA_REPO, path)
    if content:
        return json.loads(content)
    return {}

def save_json_to_repo(data, path, message):
    gh_put_file(DATA_OWNER, DATA_REPO, path, json.dumps(data, indent=4), message)

def save_csv_to_lava(df, school, department, course_code):
    now = datetime.now(FUTO_TZ).strftime("%Y-%m-%d_%H-%M")
    filename = f"{course_code}_{department.replace(' ','_')}_{now}.csv"
    path = f"attendances/{school}/{department.replace(' ','_')}/{filename}"
    csv_data = df.to_csv(index=False)
    gh_put_file(LAVA_OWNER, LAVA_REPO, path, csv_data, f"Upload attendance: {course_code} {department} {now}")

def device_registered(device_id, device_registry):
    return device_id in device_registry

def is_duplicate(name, matric, df):
    name_lower = name.strip().lower()
    if not df.empty:
        if name_lower in df["Full Name"].str.lower().values:
            return True
        if matric in df["Matric Number"].values:
            return True
    return False

# ----------------- STREAMLIT APP -----------------
st.set_page_config(page_title="ULAS - FUTO Attendance", layout="wide")

st.title("🌿 ULAS - Universal Lecture Attendance System (FUTO)")

menu = ["Student","Course Rep Login","Advisor Login"]
choice = st.sidebar.selectbox("Portal", menu)

# ----------------- STUDENT PORTAL -----------------
if choice == "Student":
    st.subheader("Student Attendance")
    school = st.selectbox("Select School", list(SCHOOL_STRUCTURE.keys()))
    department = st.selectbox("Select Department", list(SCHOOL_STRUCTURE[school].keys()))
    level = st.selectbox("Select Level", SCHOOL_STRUCTURE[school][department])
    
    # Load active attendance
    active_attendance = load_json_from_repo("active_attendance.json")
    key = f"{school}_{department}_{level}"
    if key not in active_attendance:
        st.warning("No active attendance for this level in this department.")
    else:
        token_input = st.text_input("Enter 4-digit Attendance Code")
        if st.button("Submit Code"):
            current_token = active_attendance[key]["current_token"]
            expiry = datetime.fromtimestamp(active_attendance[key]["expiry"], FUTO_TZ)
            if token_input == current_token and datetime.now(FUTO_TZ) < expiry:
                surname = st.text_input("Surname")
                other_names = st.text_input("Other Names")
                matric = st.text_input("Matric Number (11 digits)")
                device_id = st.session_state.get("device_id", str(uuid.uuid4()))
                st.session_state["device_id"] = device_id
                device_registry = load_json_from_repo("device_registry.json")
                
                if not surname or not other_names or len(matric)!=11 or not matric.isdigit():
                    st.error("Invalid input!")
                elif device_registered(device_id, device_registry):
                    st.error("This device has already submitted attendance.")
                else:
                    df = pd.DataFrame(load_json_from_repo(f"attendance_{key}.json"))
                    full_name = f"{surname} {other_names}"
                    if is_duplicate(full_name, matric, df):
                        st.error("Duplicate name or matric detected!")
                    else:
                        sn = len(df)+1
                        time_now = get_current_time()
                        df = pd.concat([df, pd.DataFrame([{"S/N":sn,"Full Name":full_name,"Matric Number":matric,"Time":time_now}])], ignore_index=True)
                        save_json_to_repo(df.to_dict(orient="records"), f"attendance_{key}.json", f"Update attendance {key}")
                        device_registry[device_id] = matric
                        save_json_to_repo(device_registry, "device_registry.json", f"Register device for {matric}")
                        st.success(f"Attendance Recorded!\nName: {full_name}\nMatric: {matric}\nTime: {time_now}")
            else:
                st.error("Invalid or expired code.")

# ----------------- COURSE REP LOGIN -----------------
elif choice == "Course Rep Login":
    st.subheader("Course Rep Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        reps = pd.read_csv("course_reps.csv") # Note: This should ideally load from GitHub ULASDATA repo
        rep = reps[(reps["username"]==username)]
        if not rep.empty:
            st.success(f"Welcome {username}")
            st.info("Rep dashboard features coming soon...")
        else:
            st.error("Invalid credentials.")

# ----------------- ADVISOR LOGIN -----------------
elif choice == "Advisor Login":
    st.subheader("Advisor Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        advisors = pd.read_csv("advisors.csv") # Ideally load from GitHub ULASDATA
        st.info("Advisor dashboard features coming soon...")

st.sidebar.info("ULAS v1.0 - FUTO Attendance System")
