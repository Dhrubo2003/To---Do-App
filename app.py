import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import time

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Smart Productivity OS", layout="wide")

FILE = "tasks.xlsx"

# -------------------- INIT EXCEL --------------------
def init_file():
    if not os.path.exists(FILE):
        df = pd.DataFrame(columns=[
            "ID","Task","Category","Priority","Status",
            "Date","Deadline","Time_Est","Time_Spent",
            "Type","Score"
        ])
        df.to_excel(FILE, index=False)

init_file()

def load_data():
    return pd.read_excel(FILE)

def save_data(df):
    df.to_excel(FILE, index=False)

# -------------------- SMART CATEGORY --------------------
def auto_category(task):
    task = task.lower()
    if "gym" in task or "workout" in task:
        return "Health"
    elif "meeting" in task or "client" in task:
        return "Work"
    elif "study" in task or "learn" in task:
        return "Learning"
    else:
        return "General"

# -------------------- PRIORITY ENGINE --------------------
def compute_priority(deadline, created_time):
    now = datetime.now()
    score = 0

    if pd.notna(deadline):
        diff = (pd.to_datetime(deadline) - now).days
        score += max(0, 10 - diff)

    age = (now - created_time).days
    score += age

    if score >= 10:
        return "Critical"
    elif score >= 5:
        return "Important"
    else:
        return "Optional"

# -------------------- DARK UI --------------------
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
.card {
    background-color: #1c1f26;
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 10px;
}
.stTextInput>div>div>input {
    background-color: #1c1f26;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# -------------------- SIDEBAR --------------------
menu = st.sidebar.radio("Navigation", ["🏠 Today", "📊 Dashboard", "🔁 Habits", "🧠 Insights"])

df = load_data()

# -------------------- FAST INPUT --------------------
st.markdown("### ⚡ Quick Add Task")

col1, col2, col3, col4 = st.columns([4,1,1,1])

with col1:
    task_input = st.text_input("Task", placeholder="Type and press Enter...")

with col2:
    est_time = st.selectbox("Time", ["15m","30m","1h","2h"])

with col3:
    deadline = st.date_input("Deadline", value=datetime.now())

with col4:
    add_btn = st.button("➕")

if add_btn and task_input:
    new_row = {
        "ID": len(df)+1,
        "Task": task_input,
        "Category": auto_category(task_input),
        "Priority": "Pending",
        "Status": "Pending",
        "Date": datetime.now(),
        "Deadline": deadline,
        "Time_Est": est_time,
        "Time_Spent": 0,
        "Type": "Task",
        "Score": 0
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.success("Task Added!")

# -------------------- TODAY --------------------
if menu == "🏠 Today":
    st.markdown("## 🔥 Do Next")

    if not df.empty:
        df["Priority"] = df.apply(
            lambda x: compute_priority(x["Deadline"], pd.to_datetime(x["Date"])), axis=1
        )

        df_sorted = df.sort_values(by="Priority")

        for i, row in df_sorted.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="card">
                <b>📝 {row['Task']}</b><br>
                ⏰ {row['Time_Est']} | 📅 {row['Deadline']} | 🔥 {row['Priority']}
                </div>
                """, unsafe_allow_html=True)

                colA, colB = st.columns(2)

                if colA.button(f"✅ Done {i}"):
                    df.at[i, "Status"] = "Completed"
                    save_data(df)

                if colB.button(f"▶ Start {i}"):
                    st.session_state["active_task"] = row["Task"]

# -------------------- DASHBOARD --------------------
elif menu == "📊 Dashboard":
    st.markdown("## 📊 Productivity Dashboard")

    if not df.empty:
        completed = df[df["Status"] == "Completed"]
        total = len(df)

        completion_rate = (len(completed)/total)*100 if total else 0

        st.metric("Completion Rate", f"{completion_rate:.2f}%")

        fig = px.histogram(df, x="Category", title="Category Distribution")
        st.plotly_chart(fig, use_container_width=True)

# -------------------- HABITS --------------------
elif menu == "🔁 Habits":
    st.markdown("## 🔁 Habit Tracker")

    habit = st.text_input("Add Habit")

    if st.button("Add Habit"):
        new_row = {
            "ID": len(df)+1,
            "Task": habit,
            "Category": "Habit",
            "Priority": "Optional",
            "Status": "Pending",
            "Date": datetime.now(),
            "Deadline": None,
            "Time_Est": "15m",
            "Time_Spent": 0,
            "Type": "Habit",
            "Score": 0
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)

# -------------------- INSIGHTS --------------------
elif menu == "🧠 Insights":
    st.markdown("## 🧠 Smart Insights")

    if not df.empty:
        pending = len(df[df["Status"] == "Pending"])

        if pending > 10:
            st.warning("⚠️ High workload detected! Possible burnout risk.")

        st.info("📊 Weekly Review (Basic)")
        st.write(f"Total Tasks: {len(df)}")
        st.write(f"Completed: {len(df[df['Status']=='Completed'])}")

# -------------------- POMODORO --------------------
st.markdown("## ⏱️ Pomodoro Timer")

if "timer" not in st.session_state:
    st.session_state.timer = 25 * 60

col1, col2 = st.columns(2)

if col1.button("Start Pomodoro"):
    for i in range(st.session_state.timer, 0, -1):
        mins, secs = divmod(i, 60)
        timer_display = f"{mins:02d}:{secs:02d}"
        st.write(timer_display)
        time.sleep(1)

if col2.button("Reset"):
    st.session_state.timer = 25 * 60
