import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Productivity OS", layout="wide")

# ------------------ UI ------------------
st.markdown("""
<style>
.stApp {background-color:#0e1117;color:white;}
.block-container {padding-top:1.5rem;}
.card {
    background:#1f2937;
    padding:15px;
    border-radius:12px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# ------------------ SESSION STATE ------------------
if "task_title" not in st.session_state:
    st.session_state.task_title = ""
    st.session_state.task_desc = ""
    st.session_state.task_type = "Personal"
    st.session_state.task_priority = "Medium"
    st.session_state.task_deadline = datetime.now()
    st.session_state.task_time = 1.0

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
    tasks = pd.DataFrame(t[1:], columns=t[0]) if len(t) > 1 else pd.DataFrame(columns=t[0])
    tasks = tasks.loc[:, tasks.columns != ""]

    if not tasks.empty:
        tasks["type"] = tasks.get("type","Personal").replace("", "Personal")
        tasks["status"] = tasks["status"].replace("", "Pending")
        tasks["priority"] = tasks["priority"].replace("", "Medium")
        tasks["category"] = tasks.get("category","General")

        tasks["est_time"] = pd.to_numeric(tasks["est_time"], errors="coerce").fillna(0)
        tasks["actual_time"] = pd.to_numeric(tasks["actual_time"], errors="coerce").fillna(0)
        tasks["deadline"] = pd.to_datetime(tasks["deadline"], errors="coerce")
        tasks["created_at"] = pd.to_datetime(tasks["created_at"], errors="coerce")

    h = sheet.worksheet("habits").get_all_values()
    habits = pd.DataFrame(h[1:], columns=h[0]) if len(h) > 1 else pd.DataFrame(columns=h[0])
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
st.sidebar.title("⚡ Productivity OS")

page = st.sidebar.radio(
    "Navigation",
    ["Tasks","Analytics","Habits","AI Review","Data Preview"]
)

# ------------------ HELPERS ------------------
def priority_score(row):
    try:
        days = (row["deadline"] - datetime.now()).days
        urgency = max(0, 10 - days)
    except:
        urgency = 5
    importance = {"High":10,"Medium":5,"Low":2}.get(row["priority"],5)
    return urgency*0.4 + importance*0.3

def categorize(text):
    text = str(text).lower()
    if "gym" in text: return "Health"
    if "meeting" in text: return "Work"
    if "read" in text: return "Learning"
    return "Personal"

# ================== TASKS ==================
if page == "Tasks":
    st.title("✅ Tasks")

    with st.form("task_form", clear_on_submit=False):

        title = st.text_input("Title", key="task_title")
        desc = st.text_area("Description", key="task_desc")
        task_type = st.selectbox("Type", ["Personal","Office"], key="task_type")
        priority = st.selectbox("Priority",["High","Medium","Low"], key="task_priority")
        deadline = st.date_input("Deadline", key="task_deadline")
        est_time = st.number_input("Hours",0.5,24.0,1.0, key="task_time")

        submitted = st.form_submit_button("Add Task")

        if submitted and title:
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
                "category": categorize(title),
                "created_at": str(datetime.now())
            }])

            tasks = pd.concat([tasks,new],ignore_index=True)
            save_tasks(tasks)

            st.success("Task Added")

            # RESET FORM
            st.session_state.task_title = ""
            st.session_state.task_desc = ""
            st.session_state.task_type = "Personal"
            st.session_state.task_priority = "Medium"
            st.session_state.task_deadline = datetime.now()
            st.session_state.task_time = 1.0

            st.rerun()

    st.divider()

    filter_type = st.selectbox("Filter", ["All","Personal","Office"])
    filtered = tasks if filter_type=="All" else tasks[tasks["type"]==filter_type]

    for i,row in filtered.iterrows():
        col1,col2,col3 = st.columns([5,1,1])

        col1.markdown(
            f"**{row['title']}**  \n"
            f"{row['type']} | {row['priority']} | {row['status']}"
        )

        if col2.button("✔", key=f"d{i}"):
            tasks.at[i,"status"] = "Done"
            tasks.at[i,"actual_time"] = row["est_time"]
            save_tasks(tasks)

        if col3.button("❌", key=f"x{i}"):
            tasks = tasks.drop(i)
            save_tasks(tasks)

# ================== ANALYTICS ==================
elif page == "Analytics":
    st.title("📊 Analytics")

    if tasks.empty:
        st.info("No data available")
    else:
        done = len(tasks[tasks["status"].str.lower()=="done"])
        total = len(tasks)
        hours = tasks["actual_time"].sum()

        score = int((done/total)*60 + min(hours/10,1)*40) if total else 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("🔥 Productivity Score", score)
        c2.metric("✅ Completed", done)
        c3.metric("📋 Total Tasks", total)
        c4.metric("⏱ Focus Hours", round(hours,2))

        st.divider()

        tasks["priority_score"] = tasks.apply(priority_score, axis=1)

        st.subheader("🔥 Top Priority Tasks")
        st.dataframe(
            tasks.sort_values("priority_score", ascending=False)
            .head(5)[["title","type","priority","deadline","priority_score"]],
            use_container_width=True
        )

        st.divider()

        col1, col2 = st.columns(2)
        col1.plotly_chart(px.pie(tasks, names="type", title="Personal vs Office"), use_container_width=True)
        col2.plotly_chart(px.pie(tasks, names="status", title="Task Status"), use_container_width=True)

        st.divider()

        col3, col4 = st.columns(2)
        col3.plotly_chart(px.histogram(tasks, x="priority", title="Priority Distribution"), use_container_width=True)
        col4.plotly_chart(px.histogram(tasks, x="type", title="Task Type Count"), use_container_width=True)

        st.divider()

        trend = tasks.groupby(tasks["created_at"].dt.date).size().reset_index(name="tasks")
        st.plotly_chart(px.line(trend, x="created_at", y="tasks", title="Task Trend"), use_container_width=True)

# ================== HABITS ==================
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

# ================== AI REVIEW ==================
elif page == "AI Review":
    st.title("🧠 Weekly Review")

    if st.button("Generate"):
        total = len(tasks)
        done = len(tasks[tasks["status"].str.lower()=="done"])

        st.write(f"Completed {done}/{total}")

        if total and done/total > 0.7:
            st.success("🔥 Great week!")
        else:
            st.warning("⚠️ Improve consistency")

# ================== DATA PREVIEW ==================
elif page == "Data Preview":
    st.title("📄 Data Preview")

    tab1, tab2 = st.tabs(["Tasks","Habits"])

    with tab1:
        st.dataframe(tasks, use_container_width=True)

    with tab2:
        st.dataframe(habits, use_container_width=True)
