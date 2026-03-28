import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Productivity OS", layout="wide")

# ---------------- UI ----------------
st.markdown("""
<style>
.stApp {background-color:#0e1117;color:white;}
.card {background:#1f2937;padding:15px;border-radius:12px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "task_title" not in st.session_state:
    st.session_state.task_title = ""
    st.session_state.task_desc = ""
    st.session_state.task_type = "Personal"
    st.session_state.task_project = ""
    st.session_state.task_priority = "Medium"
    st.session_state.task_deadline = datetime.now()
    st.session_state.task_time = 1.0

# ---------------- GOOGLE SHEETS ----------------
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds)

client = connect()
SHEET_NAME = "ProductivityOS_Data"

def load_data():
    sheet = client.open(SHEET_NAME)

    t = sheet.worksheet("tasks").get_all_values()
    tasks = pd.DataFrame(t[1:], columns=t[0]) if len(t)>1 else pd.DataFrame(columns=t[0])
    tasks = tasks.loc[:, tasks.columns != ""]

    if not tasks.empty:
        tasks["type"] = tasks.get("type","Personal").replace("", "Personal")
        tasks["project"] = tasks.get("project","")
        tasks["status"] = tasks["status"].replace("", "Pending")
        tasks["priority"] = tasks["priority"].replace("", "Medium")

        tasks["est_time"] = pd.to_numeric(tasks["est_time"], errors="coerce").fillna(0)
        tasks["actual_time"] = pd.to_numeric(tasks["actual_time"], errors="coerce").fillna(0)
        tasks["deadline"] = pd.to_datetime(tasks["deadline"], errors="coerce")
        tasks["created_at"] = pd.to_datetime(tasks["created_at"], errors="coerce")

    h = sheet.worksheet("habits").get_all_values()
    habits = pd.DataFrame(h[1:], columns=h[0]) if len(h)>1 else pd.DataFrame(columns=h[0])
    habits = habits.loc[:, habits.columns != ""]

    return tasks, habits

def save_tasks(df):
    ws = client.open(SHEET_NAME).worksheet("tasks")
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist())

def save_habits(df):
    ws = client.open(SHEET_NAME).worksheet("habits")
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist())

tasks, habits = load_data()

# ---------------- SIDEBAR ----------------
page = st.sidebar.radio("Navigation", ["Tasks","Analytics","Habits","AI Review","Data Preview"])

# ---------------- HELPERS ----------------
def priority_score(row):
    try:
        days = (row["deadline"] - datetime.now()).days
        urgency = max(0,10-days)
    except:
        urgency = 5
    importance = {"High":10,"Medium":5,"Low":2}.get(row["priority"],5)
    return urgency*0.4 + importance*0.3

def filter_data(df, option):
    now = datetime.now()

    if option == "Today":
        return df[df["created_at"].dt.date == now.date()]

    elif option == "This Week":
        start = now - timedelta(days=7)
        return df[df["created_at"] >= start]

    elif option == "This Month":
        return df[df["created_at"].dt.month == now.month]

    elif option == "Last 3 Months":
        return df[df["created_at"] >= now - timedelta(days=90)]

    elif option == "Last 1 Year":
        return df[df["created_at"] >= now - timedelta(days=365)]

    return df

# ================= TASKS =================
if page == "Tasks":
    st.title("✅ Tasks")

    with st.form("task_form", clear_on_submit=True):

        title = st.text_input("Title")
        desc = st.text_area("Description")
        task_type = st.selectbox("Type", ["Personal","Office"])
        project = st.text_input("Project (optional)")
        priority = st.selectbox("Priority",["High","Medium","Low"])
        deadline = st.date_input("Deadline")
        est_time = st.number_input("Hours",0.5,24.0,1.0)
    
        submitted = st.form_submit_button("Add Task")
    
        if submitted and title:
            new = pd.DataFrame([{
                "id": len(tasks)+1,
                "title": title,
                "desc": desc,
                "type": task_type,
                "project": project,
                "priority": priority,
                "deadline": str(deadline),
                "est_time": est_time,
                "actual_time": 0,
                "status": "Pending",
                "category": "General",
                "created_at": str(datetime.now())
            }])
    
            new = new.reindex(columns=tasks.columns, fill_value="")
    
            if tasks.empty:
                tasks = new.copy()
            else:
                tasks = pd.concat([tasks, new], ignore_index=True)
    
            save_tasks(tasks)
            st.success("Task Added")

            # RESET
            st.session_state.task_title = ""
            st.session_state.task_desc = ""
            st.session_state.task_type = "Personal"
            st.session_state.task_project = ""
            st.session_state.task_priority = "Medium"
            st.session_state.task_deadline = datetime.now()
            st.session_state.task_time = 1.0

            st.rerun()

    st.divider()

    for i,row in tasks.iterrows():
        col1,col2,col3 = st.columns([5,1,1])
        col1.markdown(f"**{row['title']}**  \n{row['type']} | {row['project']} | {row['priority']}")

        if col2.button("✔", key=f"d{i}"):
            tasks.at[i,"status"] = "Done"
            tasks.at[i,"actual_time"] = row["est_time"]
            save_tasks(tasks)

        if col3.button("❌", key=f"x{i}"):
            tasks = tasks.drop(i)
            save_tasks(tasks)

# ================= ANALYTICS =================
elif page == "Analytics":
    st.title("📊 Analytics")

    option = st.selectbox("Filter Time",
        ["Today","This Week","This Month","Last 3 Months","Last 1 Year","All"]
    )

    df = filter_data(tasks, option)

    if df.empty:
        st.info("No data for selected period")
    else:
        done = len(df[df["status"].str.lower()=="done"])
        total = len(df)
        hours = df["actual_time"].sum()

        c1,c2,c3 = st.columns(3)
        c1.metric("Completed", done)
        c2.metric("Total", total)
        c3.metric("Hours", round(hours,2))

        st.plotly_chart(px.pie(df, names="type", title="Work Split"), use_container_width=True)
        st.plotly_chart(px.pie(df, names="status", title="Status"), use_container_width=True)

        st.plotly_chart(px.histogram(df, x="priority", title="Priority"), use_container_width=True)

        if "project" in df.columns:
            st.plotly_chart(px.histogram(df, x="project", title="Projects"), use_container_width=True)

        trend = df.groupby(df["created_at"].dt.date).size().reset_index(name="tasks")
        st.plotly_chart(px.line(trend, x="created_at", y="tasks", title="Trend"), use_container_width=True)

# ================= HABITS =================
elif page == "Habits":
    st.title("🔁 Habits")

    with st.form("habit"):
        name = st.text_input("Habit")
        if st.form_submit_button("Add"):
            new = pd.DataFrame([{
                "id": len(habits)+1,
                "name": name,
                "streak": 0
            }])
            habits = pd.concat([habits,new],ignore_index=True)
            save_habits(habits)

    for i,row in habits.iterrows():
        col1,col2 = st.columns([4,1])
        col1.write(f"{row['name']} 🔥 {row['streak']}")
        if col2.button("Done", key=f"h{i}"):
            habits.at[i,"streak"] += 1
            save_habits(habits)

# ================= AI REVIEW =================
elif page == "AI Review":
    st.title("🧠 Weekly Review")

    if st.button("Generate"):
        total = len(tasks)
        done = len(tasks[tasks["status"].str.lower()=="done"])

        st.write(f"Completed {done}/{total}")

# ================= DATA =================
elif page == "Data Preview":
    st.dataframe(tasks)
