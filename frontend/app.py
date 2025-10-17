import streamlit as st
import requests
import pandas as pd
from streamlit_calendar import calendar as st_calendar
import plotly.express as px
import os

# ====================================================
# ⚙️ CONFIGURATION
# ====================================================
API_BASE = st.secrets.get("API_BASE") or os.environ.get("API_BASE") or "http://127.0.0.1:8000"
st.set_page_config(page_title="Family Calendar AI", layout="wide")

st.title("🧭 Family Calendar AI")
st.caption("Plan, track, and visualize your family’s schedule — all in one place.")


# ====================================================
# 🔐 AUTHENTICATION
# ====================================================
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None

# Login / Register UI
if not st.session_state["user_email"]:
    st.subheader("🔐 Sign in to Family Calendar AI")

    mode = st.radio("Choose:", ["Login", "Register"], horizontal=True)
    email = st.text_input("Email Address", placeholder="you@example.com")

    if mode == "Register":
        if st.button("Create Account"):
            r = requests.post(f"{API_BASE}/auth/register", json={"email": email})
            if r.status_code == 200:
                st.success("✅ Account created successfully! Please log in.")
            else:
                st.error(r.json().get("detail", "Registration failed."))
    else:
        if st.button("Login"):
            r = requests.post(f"{API_BASE}/auth/login", json={"email": email})
            if r.status_code == 200:
                st.session_state["user_email"] = email.strip().lower()
                st.success(f"Welcome back, {email}! 🎉")
                st.rerun()
            else:
                st.error("Invalid credentials or user not registered.")
    st.stop()


# ====================================================
# 📂 SIDEBAR NAVIGATION
# ====================================================
with st.sidebar:
    st.markdown(f"👤 **{st.session_state['user_email']}**")
    if st.button("🚪 Log out"):
        st.session_state.clear()
        st.rerun()

st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["📅 Calendar", "📊 Analytics"])


# ====================================================
# 📅 CALENDAR PAGE
# ====================================================
headers = {"X-User-Email": st.session_state["user_email"]}

if page == "📅 Calendar":
    try:
        resp = requests.get(f"{API_BASE}/tasks", headers=headers)
        tasks = resp.json().get("tasks", []) if resp.status_code == 200 else []
    except Exception as e:
        st.error(f"⚠️ Could not connect to backend: {e}")
        tasks = []

    if not tasks:
        st.info("📭 No tasks yet. Add some below!")
    else:
        color_map = {"High": "#e74c3c", "Medium": "#f1c40f", "Low": "#2ecc71"}
        events = [
            {
                "title": t["title"],
                "start": t["due_date"],
                "end": t["due_date"],
                "color": color_map.get(t["priority"], "#95a5a6"),
                "extendedProps": {
                    "category": t["category"],
                    "description": t["description"],
                    "priority": t["priority"],
                    "status": t["status"]
                }
            }
            for t in tasks if t.get("due_date")
        ]

        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay"
            },
            "height": 650,
        }

        st_calendar(events=events, options=calendar_options, key="calendar_ui")
        st.markdown("🟢 **Low** 🟡 **Medium** 🔴 **High**")

    # ----------------------------------------------------
    # QUICK ACTIONS
    # ----------------------------------------------------
    st.markdown("---")
    st.subheader("⚡ Quick Actions")

    action = st.selectbox(
        "Select Action",
        ["None", "➕ Add Task", "✏️ Update Task", "🗑️ Delete Task", "🤖 AI Tools"],
        index=0,
    )

    # ----------------------------- ADD TASK -----------------------------
    if action == "➕ Add Task":
        st.markdown("### ➕ Add New Task")
        title = st.text_input("Title")
        description = st.text_area("Description")
        category = st.text_input("Category")
        due_date = st.date_input("Due Date", value=None)
        due_date = due_date.strftime("%Y-%m-%d") if due_date else None

        if st.button("Suggest Priority 🤖"):
            try:
                payload = {"title": title, "description": description, "due_date": due_date}
                resp = requests.post(f"{API_BASE}/ai/priority", json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state["ai_priority"] = result.get("priority", "Medium")
                    st.info(f"🧠 Suggested Priority: **{st.session_state['ai_priority']}**")
                else:
                    st.warning("⚠️ AI could not suggest priority.")
            except Exception as e:
                st.error(f"AI Error: {e}")

        priority = st.selectbox(
            "Priority",
            ["Low", "Medium", "High"],
            index=["Low", "Medium", "High"].index(st.session_state.get("ai_priority", "Medium")),
        )
        reminder_days = st.number_input("Reminder Days", min_value=0, value=1, step=1)

        if st.button("✅ Add Task"):
            data = {
                "title": title,
                "description": description,
                "category": category,
                "due_date": due_date,
                "priority": priority,
                "reminder_days": reminder_days,
            }
            r = requests.post(f"{API_BASE}/tasks", json=data, headers=headers)
            if r.status_code == 200:
                st.success("✅ Task added successfully!")
                st.session_state.pop("ai_priority", None)
                st.rerun()
            else:
                st.error(f"⚠️ Failed to add task ({r.status_code})")

    # ----------------------------- DELETE TASK -----------------------------
    elif action == "🗑️ Delete Task":
        if not tasks:
            st.info("No tasks to delete.")
        else:
            st.markdown("### 🗑️ Delete a Task")
            task_choices = {f"{t['title']} (ID: {t['task_id']})": t["task_id"] for t in tasks}
            selected_task = st.selectbox("Select Task", list(task_choices.keys()))
            task_id = task_choices[selected_task]
            if st.button("🧹 Confirm Delete"):
                resp = requests.delete(f"{API_BASE}/tasks/{task_id}", headers=headers)
                if resp.status_code == 200:
                    st.success("🗑️ Task deleted successfully!")
                    st.rerun()
                else:
                    st.error("⚠️ Failed to delete task.")


# ====================================================
# 📊 ANALYTICS PAGE
# ====================================================
elif page == "📊 Analytics":
    st.header("📊 Analytics Dashboard")

    try:
        resp = requests.get(f"{API_BASE}/tasks", headers=headers)
        tasks = resp.json().get("tasks", []) if resp.status_code == 200 else []
    except Exception as e:
        st.error(f"⚠️ Could not load tasks: {e}")
        tasks = []

    if not tasks:
        st.info("📭 No data available for analytics.")
    else:
        df = pd.DataFrame(tasks)
        if "due_date" in df.columns:
            df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")

        today = pd.Timestamp.today().normalize()
        st.markdown("### 📆 Filter by Due Date Range")

        min_date, max_date = df["due_date"].min(), df["due_date"].max()
        if pd.isna(min_date): min_date = today - pd.Timedelta(days=30)
        if pd.isna(max_date): max_date = today

        preset = st.selectbox("Preset Range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"], index=1)
        if preset == "Last 7 days":
            start_date, end_date = today - pd.Timedelta(days=7), today
        elif preset == "Last 90 days":
            start_date, end_date = today - pd.Timedelta(days=90), today
        elif preset == "All time":
            start_date, end_date = min_date, max_date
        else:
            start_date, end_date = today - pd.Timedelta(days=30), today

        start_date, end_date = st.date_input("Custom date range:", value=(start_date, end_date), min_value=min_date, max_value=max_date)
        df_filtered = df[(df["due_date"] >= pd.to_datetime(start_date)) & (df["due_date"] <= pd.to_datetime(end_date))].copy()

        if not df_filtered.empty:
            total = len(df_filtered)
            completed = len(df_filtered[df_filtered["status"].str.lower() == "completed"])
            overdue = len(df_filtered[(df_filtered["due_date"] < today) & (df_filtered["status"].str.lower() != "completed")])
            recurring = len(df_filtered[df_filtered["title"].str.contains("weekly|every", case=False, na=False)])

            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Completion Rate", f"{(completed/total)*100:.1f}%")
            col2.metric("⚠️ Overdue Rate", f"{(overdue/total)*100:.1f}%")
            col3.metric("🔁 Recurring", f"{(recurring/total)*100:.1f}%")

            st.subheader("📊 Task Distribution")
            if "priority" in df_filtered.columns:
                st.plotly_chart(px.pie(df_filtered, names="priority", title="Priority Distribution", hole=0.4), use_container_width=True)
            st.plotly_chart(px.bar(df_filtered, x="status", color="status", title="Status Overview", text_auto=True), use_container_width=True)


# ====================================================
# 🧠 AI SUMMARY
# ====================================================
st.markdown("---")
st.subheader("🧠 AI Summary")

if st.button("✨ Generate Smart Summary"):
    try:
        resp = requests.get(f"{API_BASE}/ai/summary", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            st.success("✅ Summary generated!")
            st.markdown(data.get("summary", ""))
            stats = data.get("stats", {})
            if stats:
                col1, col2, col3 = st.columns(3)
                col1.metric("🗂️ Total", stats.get("total", 0))
                col2.metric("✅ Completed", stats.get("completed", 0))
                col3.metric("⚠️ Overdue", stats.get("overdue", 0))
        else:
            st.error("⚠️ Could not fetch summary.")
    except Exception as e:
        st.error(f"Error fetching summary: {e}")
