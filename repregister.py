import streamlit as st
import pandas as pd
import os
import hashlib

SCHOOLS_FILE = "schools.csv"
DEPARTMENTS_FILE = "departments.csv"
REPS_FILE = "reps.csv"

REP_COLS = ["username", "password", "school", "department", "level"]

LEVELS = ["100", "200", "300", "400", "500"]

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

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()
def rep_register():
    st.title("ULAS — Course Rep Registration")

    schools = load_csv(SCHOOLS_FILE, ["name"])
    if schools.empty:
        st.error("schools.csv not found or empty")
        return

    departments = load_csv(DEPARTMENTS_FILE, ["school", "department"])
    if departments.empty:
        st.error("departments.csv not found or empty")
        return

    reps = load_csv(REPS_FILE, REP_COLS)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    school = st.selectbox("School", schools["name"])

    dept_options = departments[
        departments["school"] == school
    ]["department"]

    department = st.selectbox("Department", dept_options)

    level = st.selectbox("Level", LEVELS)

    if st.button("Register Course Rep"):
        if not username or not password:
            st.error("Username and password required")
            return

        if username in reps["username"].values:
            st.error("Username already exists")
            return

        reps.loc[len(reps)] = [
            username,
            hash_password(password),
            school,
            department,
            level
        ]

        save_csv(reps, REPS_FILE)
        st.success("Course rep registered successfully")
def rep_list():
    st.subheader("Registered Course Reps")

    reps = load_csv(REPS_FILE, REP_COLS)
    if reps.empty:
        st.info("No reps registered yet")
        return

    st.dataframe(
        reps[["username", "school", "department", "level"]]
    )

def main():
    page = st.sidebar.selectbox(
        "Page",
        ["Register Rep", "View Reps"]
    )

    if page == "Register Rep":
        rep_register()
    else:
        rep_list()

if __name__ == "__main__":
    main()
