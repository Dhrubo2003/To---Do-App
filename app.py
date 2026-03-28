import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Productivity OS", layout="wide")

# ------------------ DARK UI ------------------
st.markdown("""
    <style>
    body {background-color: #0e1117; color: white;}
    .stApp {background-color: #0e1117;}
    .css-1d391kg {background-color: #111827;}
    .card {
        padding: 15px;
        border-radius: 12px;
        background-color: #1f2937;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ GOOGLE SHEETS CONNECT ------------------
@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    client = gspread.authorize(creds)
    return client

client = connect_sheet()

SHEET_NAME = "ProductivityOS_Data"

def load_data():
    sheet = client.open(SHEET_NAME)
    tasks = pd.DataFrame(sheet.worksheet("tasks").get_all_records())
    habits = pd.DataFrame(sheet.worksheet("habits").get_all_records())
    return tasks, habits

def save_tasks(df):
    sheet = client.open(SHEET_NAME).worksheet("tasks")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def save_habits(df):
    sheet = client.open(SHEET_NAME).worksheet("habits")
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

tasks, habits = load_data()

# ------------------ SIDEBAR ------------------
st.sidebar.title("⚡ Productivity OS")
page = st.sidebar.radio("", ["Dashboard","Tasks","Habits","Insights","AI Review"])

# ------------------ HELPERS ------------------
def priority_score(row):
    try:
        days_left = (pd.to_datetime(row["deadline"]) - datetime.now()).days
        urgency = max(0, 10 - days_left)
    except:
        urgency = 5

    importance = {"High":10,"Medium":5,"Low":2}.get(row.get("priority","Medium"),5)
    effort = row.get("est_time",1)

    return urgency*0.4 + importance*0.3 - effort*0.2

def categorize(text):
    text = str(text).lower()
    if "gym" in text or "run" in text:
        return "Health"
    if "meeting" in text or "client" in text:
        return "Work"
    if "read" in text or "study" in text:
        return "Learning"
    return "Personal"

# ------------------ DASHBOARD ------------------
if page == "Dashboard":
    st.title("📊 Dashboard")

    if len(tasks) > 0:
        tasks["status"] = tasks["status"].fillna("Pending")

        completed = len(tasks[tasks["status"]=="Done"])
        total = len(tasks)

        completion_rate = completed / total if total else 0
        focus_hours = pd.to_numeric(tasks["actual_time"], errors='coerce').sum()

        score = int((completion_rate*0.6 + min(focus_hours/10,1)*0.4)*100)

        col1, col2, col3 = st.columns(3)
        col1.metric("🔥 Score", score)
        col2.metric("✅ Completed", completed)
        col3.metric("⏱ Hours", round(focus_hours,2))

        tasks["priority_score"] = tasks.apply(priority_score, axis=1)
        top = tasks.sort_values("priority_score", ascending=False).head(5)

        st.subheader("🔥 Do Now")
        st.dataframe(top[["title","priority","deadline","priority_score"]])

        # Burnout Detection
        if total > 8 and completion_rate < 0.5:
            st.warning("⚠️ You're overloaded. Reduce tasks.")

# ------------------ TASKS ------------------
elif page == "Tasks":
    st.title("✅ Tasks")

    with st.form("add_task"):
        title = st.text_input("Title")
        desc = st.text_area("Description")
        priority = st.selectbox("Priority",["High","Medium","Low"])
        deadline = st.date_input("Deadline")
        est_time = st.number_input("Est Hours",0.5,24.0,1.0)
        submit = st.form_submit_button("Add Task")

        if submit:
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
            st.success("Task Added!")

    for i,row in tasks.iterrows():
        col1,col2,col3 = st.columns([4,1,1])
        col1.markdown(f"**{row['title']}** ({row['category']})")

        if col2.button("✔", key=f"done{i}"):
            tasks.at[i,"status"] = "Done"
            tasks.at[i,"actual_time"] = row.get("est_time",1)
            save_tasks(tasks)

        if col3.button("❌", key=f"del{i}"):
            tasks = tasks.drop(i)
            save_tasks(tasks)

# ------------------ HABITS ------------------
elif page == "Habits":
    st.title("🔁 Habits")

    with st.form("habit"):
        name = st.text_input("Habit Name")
        submit = st.form_submit_button("Add")

        if submit:
            new = pd.DataFrame([{
                "id": len(habits)+1,
                "name": name,
                "streak": 0,
                "last_done": "",
                "consistency": 0
            }])
            habits = pd.concat([habits, new], ignore_index=True)
            save_habits(habits)

    for i,row in habits.iterrows():
        col1,col2 = st.columns([4,1])
        col1.write(f"{row['name']} 🔥 {row['streak']}")

        if col2.button("Done", key=f"h{i}"):
            habits.at[i,"streak"] += 1
            habits.at[i,"last_done"] = str(datetime.now())
            save_habits(habits)

# ------------------ INSIGHTS ------------------
elif page == "Insights":
    st.title("📈 Insights")

    if len(tasks) > 0:
        fig1 = px.histogram(tasks, x="category")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(tasks, names="status")
        st.plotly_chart(fig2, use_container_width=True)

# ------------------ AI REVIEW ------------------
elif page == "AI Review":
    st.title("🧠 Weekly Review")

    if st.button("Generate"):
        completed = len(tasks[tasks["status"]=="Done"])
        total = len(tasks)

        st.write(f"Completed {completed}/{total} tasks")

        if total > 0 and completed/total > 0.7:
            st.success("🔥 Great week!")
        else:
            st.warning("⚠️ Improve consistency")

        st.write("💡 Suggestions:")
        st.write("- Focus on high priority")
        st.write("- Avoid overload")
        st.write("- Maintain habits")
