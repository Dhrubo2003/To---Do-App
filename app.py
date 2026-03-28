import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import os

st.set_page_config(page_title="Productivity OS", layout="wide")

FILE = "data.xlsx"

# ------------------ INIT EXCEL ------------------
def init_file():
    if not os.path.exists(FILE):
        tasks = pd.DataFrame(columns=[
            "id","title","desc","priority","deadline",
            "est_time","actual_time","status",
            "category","created_at"
        ])
        habits = pd.DataFrame(columns=[
            "id","name","streak","last_done","consistency"
        ])
        with pd.ExcelWriter(FILE) as writer:
            tasks.to_excel(writer, sheet_name="tasks", index=False)
            habits.to_excel(writer, sheet_name="habits", index=False)

def load_data():
    tasks = pd.read_excel(FILE, sheet_name="tasks")
    habits = pd.read_excel(FILE, sheet_name="habits")
    return tasks, habits

def save_data(tasks, habits):
    with pd.ExcelWriter(FILE, engine='openpyxl', mode='w') as writer:
        tasks.to_excel(writer, sheet_name="tasks", index=False)
        habits.to_excel(writer, sheet_name="habits", index=False)

init_file()
tasks, habits = load_data()

# ------------------ SIDEBAR ------------------
st.sidebar.title("⚡ Productivity OS")
page = st.sidebar.radio("Navigate", [
    "Dashboard","Tasks","Habits","Planner","Insights","AI Review"
])

# ------------------ HELPERS ------------------

def priority_score(row):
    if pd.isna(row["deadline"]):
        return 0
    days_left = (pd.to_datetime(row["deadline"]) - datetime.now()).days
    urgency = max(0, 10 - days_left)
    importance = {"High":10,"Medium":5,"Low":2}.get(row["priority"],5)
    effort = row["est_time"] if not pd.isna(row["est_time"]) else 1
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
        completed = len(tasks[tasks["status"]=="Done"])
        total = len(tasks)
        completion_rate = completed/total if total>0 else 0

        on_time = len(tasks[(tasks["status"]=="Done") & 
                   (pd.to_datetime(tasks["deadline"]) >= pd.to_datetime(tasks["created_at"]))])
        on_time_rate = on_time/total if total>0 else 0

        focus_hours = tasks["actual_time"].sum() if "actual_time" in tasks else 0

        score = int((completion_rate*0.5 + on_time_rate*0.3 + min(focus_hours/10,1)*0.2)*100)

        col1,col2,col3 = st.columns(3)
        col1.metric("🔥 Productivity Score", score)
        col2.metric("✅ Completed Tasks", completed)
        col3.metric("⏱ Focus Hours", round(focus_hours,2))

        tasks["priority_score"] = tasks.apply(priority_score, axis=1)
        top_tasks = tasks.sort_values("priority_score", ascending=False).head(5)

        st.subheader("🔥 Do Now")
        st.dataframe(top_tasks[["title","priority","deadline","priority_score"]])

        # Burnout Detection
        if total > 8 and completion_rate < 0.5:
            st.warning("⚠️ High workload detected. Consider reducing tasks.")

# ------------------ TASKS ------------------
elif page == "Tasks":
    st.title("✅ Task Manager")

    with st.form("task_form"):
        title = st.text_input("Title")
        desc = st.text_area("Description")
        priority = st.selectbox("Priority",["High","Medium","Low"])
        deadline = st.date_input("Deadline")
        est_time = st.number_input("Estimated Hours",0.5,24.0,1.0)
        submit = st.form_submit_button("Add Task")

        if submit:
            new = {
                "id": len(tasks)+1,
                "title": title,
                "desc": desc,
                "priority": priority,
                "deadline": deadline,
                "est_time": est_time,
                "actual_time": 0,
                "status": "Pending",
                "category": categorize(title),
                "created_at": datetime.now()
            }
            tasks = pd.concat([tasks, pd.DataFrame([new])], ignore_index=True)
            save_data(tasks, habits)
            st.success("Task Added!")

    st.subheader("Your Tasks")

    for i,row in tasks.iterrows():
        col1,col2,col3 = st.columns([4,1,1])
        col1.write(f"**{row['title']}** ({row['category']})")

        if col2.button("✔", key=f"done{i}"):
            tasks.at[i,"status"] = "Done"
            tasks.at[i,"actual_time"] = row["est_time"]
            save_data(tasks, habits)

        if col3.button("❌", key=f"del{i}"):
            tasks = tasks.drop(i)
            save_data(tasks, habits)

# ------------------ HABITS ------------------
elif page == "Habits":
    st.title("🔁 Habits")

    with st.form("habit_form"):
        name = st.text_input("Habit Name")
        submit = st.form_submit_button("Add Habit")

        if submit:
            new = {
                "id": len(habits)+1,
                "name": name,
                "streak": 0,
                "last_done": None,
                "consistency": 0
            }
            habits = pd.concat([habits, pd.DataFrame([new])], ignore_index=True)
            save_data(tasks, habits)

    for i,row in habits.iterrows():
        col1,col2 = st.columns([4,1])
        col1.write(f"{row['name']} 🔥 {row['streak']}")

        if col2.button("Done", key=f"habit{i}"):
            habits.at[i,"streak"] += 1
            habits.at[i,"last_done"] = datetime.now()
            save_data(tasks, habits)

# ------------------ PLANNER ------------------
elif page == "Planner":
    st.title("📅 Planner")

    today = datetime.now().date()
    today_tasks = tasks[pd.to_datetime(tasks["deadline"]).dt.date == today]

    st.write("### Today's Tasks")
    st.dataframe(today_tasks[["title","priority","status"]])

# ------------------ INSIGHTS ------------------
elif page == "Insights":
    st.title("📈 Insights")

    if len(tasks) > 0:
        fig = px.histogram(tasks, x="category")
        st.plotly_chart(fig)

        status_fig = px.pie(tasks, names="status")
        st.plotly_chart(status_fig)

# ------------------ AI REVIEW ------------------
elif page == "AI Review":
    st.title("🧠 Weekly Review")

    if st.button("Generate Review"):
        completed = len(tasks[tasks["status"]=="Done"])
        total = len(tasks)

        st.write("### 📌 Summary")
        st.write(f"- Completed {completed}/{total} tasks")

        if completed/total > 0.7:
            st.success("🔥 Great productivity this week!")
        else:
            st.warning("⚠️ Try improving consistency.")

        st.write("### 💡 Suggestions")
        st.write("- Reduce overload")
        st.write("- Focus on high priority tasks")
        st.write("- Maintain habit streaks")
