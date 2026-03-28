import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Productivity OS", layout="wide")

# ------------------ UI ------------------
st.markdown("""
<style>
.stApp {background-color:#0e1117;color:white;}
.card {background:#1f2937;padding:15px;border-radius:12px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ------------------ GOOGLE SHEETS ------------------
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
        tasks["status"] = tasks["status"].replace("", "Pending")
        tasks["priority"] = tasks["priority"].replace("", "Medium")

        tasks["est_time"] = pd.to_numeric(tasks["est_time"], errors="coerce").fillna(0)
        tasks["actual_time"] = pd.to_numeric(tasks["actual_time"], errors="coerce").fillna(0)
        tasks["deadline"] = pd.to_datetime(tasks["deadline"], errors="coerce")

    h = sheet.worksheet("habits").get_all_values()
    habits = pd.DataFrame(h[1:], columns=h[0]) if len(h)>1 else pd.DataFrame(columns=h[0])
    habits = habits.loc[:, habits.columns != ""]

    if not habits.empty:
        habits["streak"] = pd.to_numeric(habits["streak"], errors="coerce").fillna(0)

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

# ------------------ SIDEBAR ------------------
page = st.sidebar.radio(
    "Navigation",
    ["Tasks","Dashboard","Habits","Insights","AI Review","Data Preview"]
)

# ------------------ HELPERS ------------------
def priority_score(row):
    try:
        days = (row["deadline"] - datetime.now()).days
        urgency = max(0,10-days)
    except:
        urgency = 5
    importance = {"High":10,"Medium":5,"Low":2}.get(row["priority"],5)
    return urgency*0.4 + importance*0.3

# ================= TASKS =================
if page == "Tasks":
    st.title("✅ Tasks")

    with st.form("task"):
        title = st.text_input("Title")
        desc = st.text_area("Description")
        task_type = st.selectbox("Type", ["Personal","Office"])
        priority = st.selectbox("Priority",["High","Medium","Low"])
        deadline = st.date_input("Deadline")
        est_time = st.number_input("Hours",0.5,24.0,1.0)

        if st.form_submit_button("Add Task"):
            new = pd.DataFrame([{
                "id": len(tasks)+1,
                "title": title,
                "desc": desc,
                "type": task_type,
                "priority": priority,
                "deadline": str(deadline),
                "est_time": est_time,
                "actual_time": 0,
                "status": "Pending",
                "category": "General",
                "created_at": str(datetime.now())
            }])
            tasks = pd.concat([tasks,new],ignore_index=True)
            save_tasks(tasks)
            st.success("Task Added")

    st.divider()

    # FILTER
    filter_type = st.selectbox("Filter", ["All","Personal","Office"])

    filtered = tasks if filter_type=="All" else tasks[tasks["type"]==filter_type]

    for i,row in filtered.iterrows():
        col1,col2,col3 = st.columns([5,1,1])
        col1.markdown(f"**{row['title']}**  \n{row['type']} | {row['priority']}")

        if col2.button("✔", key=f"d{i}"):
            tasks.at[i,"status"] = "Done"
            save_tasks(tasks)

        if col3.button("❌", key=f"x{i}"):
            tasks = tasks.drop(i)
            save_tasks(tasks)

# ================= DASHBOARD =================
elif page == "Dashboard":
    st.title("📊 Dashboard")

    if tasks.empty:
        st.info("No data")
    else:
        done = len(tasks[tasks["status"].str.lower()=="done"])
        total = len(tasks)

        col1,col2 = st.columns(2)
        col1.metric("Completed", done)
        col2.metric("Total", total)

        fig = px.pie(tasks, names="type", title="Personal vs Office")
        st.plotly_chart(fig, use_container_width=True)

# ================= HABITS =================
elif page == "Habits":
    st.title("🔁 Habits")

    with st.form("habit"):
        name = st.text_input("Habit")
        if st.form_submit_button("Add"):
            new = pd.DataFrame([{
                "id": len(habits)+1,
                "name": name,
                "streak": 0,
                "last_done": "",
                "consistency": 0
            }])
            habits = pd.concat([habits,new],ignore_index=True)
            save_habits(habits)

    for i,row in habits.iterrows():
        col1,col2 = st.columns([4,1])
        col1.write(f"{row['name']} 🔥 {row['streak']}")
        if col2.button("Done", key=f"h{i}"):
            habits.at[i,"streak"] += 1
            save_habits(habits)

# ================= INSIGHTS =================
elif page == "Insights":
    st.title("📈 Insights")

    if not tasks.empty:
        st.plotly_chart(px.histogram(tasks,x="type"),use_container_width=True)

# ================= DATA =================
elif page == "Data Preview":
    st.dataframe(tasks)
