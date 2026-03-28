import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Productivity OS", layout="wide")

# ------------------ UI STYLE ------------------
st.markdown("""
<style>
.stApp {background-color: #0e1117; color: #fff;}
.block-container {padding-top: 1.5rem;}
.card {
    padding: 15px;
    border-radius: 15px;
    background-color: #1f2937;
    margin-bottom: 10px;
}
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

    # TASKS
    t = sheet.worksheet("tasks").get_all_values()
    tasks = pd.DataFrame(t[1:], columns=t[0]) if len(t) > 1 else pd.DataFrame(columns=t[0])
    tasks = tasks.loc[:, tasks.columns != ""]

    if not tasks.empty:
        tasks["status"] = tasks["status"].replace("", "Pending")
        tasks["priority"] = tasks["priority"].replace("", "Medium")
        tasks["category"] = tasks["category"].replace("", "Other")

        tasks["est_time"] = pd.to_numeric(tasks["est_time"], errors="coerce").fillna(0)
        tasks["actual_time"] = pd.to_numeric(tasks["actual_time"], errors="coerce").fillna(0)
        tasks["deadline"] = pd.to_datetime(tasks["deadline"], errors="coerce")

    # HABITS
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
    ["Tasks", "Dashboard", "Habits", "Insights", "AI Review", "Data Preview"]
)

# ------------------ HELPERS ------------------
def priority_score(row):
    try:
        days_left = (row["deadline"] - datetime.now()).days
        urgency = max(0, 10 - days_left)
    except:
        urgency = 5

    importance = {"High":10,"Medium":5,"Low":2}.get(row["priority"],5)
    effort = row["est_time"] if row["est_time"] else 1

    return urgency*0.4 + importance*0.3 - effort*0.2

def categorize(text):
    text = str(text).lower()
    if "gym" in text: return "Health"
    if "meeting" in text: return "Work"
    if "read" in text: return "Learning"
    return "Personal"

# ================== TASKS ==================
if page == "Tasks":
    st.title("✅ Tasks")

    with st.form("task"):
        title = st.text_input("Title")
        desc = st.text_area("Description")
        priority = st.selectbox("Priority",["High","Medium","Low"])
        deadline = st.date_input("Deadline")
        est_time = st.number_input("Hours",0.5,24.0,1.0)

        if st.form_submit_button("Add Task"):
            new = pd.DataFrame([{
                "id": len(tasks)+1,
                "title": title,
                "desc": desc,
                "priority": priority,
                "deadline": str(deadline),
                "est_time": est_time,
                "actual_time": 0,
                "status": "Pending",
                "category": categorize(title),
                "created_at": str(datetime.now())
            }])
            tasks = pd.concat([tasks, new], ignore_index=True)
            save_tasks(tasks)
            st.success("Task Added")

    st.divider()

    for i,row in tasks.iterrows():
        with st.container():
            col1,col2,col3 = st.columns([5,1,1])
            col1.markdown(f"**{row['title']}**  \n*{row['category']} | {row['priority']}*")

            if col2.button("✔", key=f"d{i}"):
                tasks.at[i,"status"] = "Done"
                tasks.at[i,"actual_time"] = row["est_time"]
                save_tasks(tasks)

            if col3.button("❌", key=f"x{i}"):
                tasks = tasks.drop(i)
                save_tasks(tasks)

# ================== DASHBOARD ==================
elif page == "Dashboard":
    st.title("📊 Dashboard")

    if tasks.empty:
        st.info("No tasks yet.")
    else:
        completed = len(tasks[tasks["status"].str.lower()=="done"])
        total = len(tasks)
        hours = tasks["actual_time"].sum()

        score = int((completed/total)*60 + min(hours/10,1)*40)

        c1,c2,c3 = st.columns(3)
        c1.metric("🔥 Score", score)
        c2.metric("✅ Completed", completed)
        c3.metric("⏱ Hours", round(hours,2))

        tasks["priority_score"] = tasks.apply(priority_score, axis=1)
        st.subheader("🔥 Do Now")
        st.dataframe(tasks.sort_values("priority_score",ascending=False).head(5))

        if total > 8 and completed/total < 0.5:
            st.warning("⚠️ Burnout risk")

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
            habits.at[i,"last_done"] = str(datetime.now())
            save_habits(habits)

# ================== INSIGHTS ==================
elif page == "Insights":
    st.title("📈 Insights")

    if tasks.empty:
        st.info("No data yet")
    else:
        st.plotly_chart(px.histogram(tasks, x="category"), use_container_width=True)
        st.plotly_chart(px.pie(tasks, names="status"), use_container_width=True)

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

    tab1, tab2 = st.tabs(["Tasks Sheet", "Habits Sheet"])

    with tab1:
        st.dataframe(tasks, use_container_width=True)

    with tab2:
        st.dataframe(habits, use_container_width=True)
