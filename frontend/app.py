import streamlit as st
import requests
import pandas as pd
from streamlit_calendar import calendar as st_calendar
import plotly.express as px
import os

# ====================================================
# 🧠 CONFIGURATION
# ====================================================
API_BASE = st.secrets.get("API_BASE") or os.environ.get("API_BASE") or "http://127.0.0.1:8000"

st.set_page_config(page_title="Family Calendar AI", layout="wide")
st.title("🧭 Family Calendar AI")
st.caption("Plan, track, and visualize your family’s schedule — all in one place.")

# ====================================================
# 📂 SIDEBAR NAVIGATION
# ====================================================
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["📅 Calendar", "📊 Analytics"])

# ====================================================
# 📅 CALENDAR PAGE
# ====================================================
if page == "📅 Calendar":
    try:
        resp = requests.get(f"{API_BASE}/tasks")
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
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
            "editable": False,
            "selectable": True,
            "height": 650,
        }

        st_calendar(events=events, options=calendar_options, key="calendar_ui")
        st.markdown("🟢 **Low Priority** 🟡 **Medium Priority** 🔴 **High Priority**")

    # ----------------------------------------------------
    # QUICK ACTIONS MENU
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
        due_date = st.date_input("Due Date (optional)", value=None)
        due_date = due_date.strftime("%Y-%m-%d") if due_date else None
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        reminder_days = st.number_input("Reminder Days", min_value=0, value=1)

        if st.button("✅ Add Task"):
            try:
                data = {
                    "title": title,
                    "description": description,
                    "category": category,
                    "due_date": due_date,
                    "priority": priority,
                    "reminder_days": reminder_days,
                }
                r = requests.post(f"{API_BASE}/tasks", json=data)
                if r.status_code == 200:
                    st.success("✅ Task added successfully!")
                    st.session_state["refresh_summary"] = True
                else:
                    st.error(f"⚠️ Failed to add task ({r.status_code})")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # ----------------------------- UPDATE TASK -----------------------------
    elif action == "✏️ Update Task":
        if not tasks:
            st.info("No tasks found to update.")
        else:
            st.markdown("### ✏️ Update Task")
            task_choices = {f"{t['title']} (ID: {t['task_id']})": t["task_id"] for t in tasks}
            selected_task = st.selectbox("Select Task", list(task_choices.keys()))
            task_id = task_choices[selected_task]

            updates = {}
            new_title = st.text_input("New Title")
            new_description = st.text_area("New Description")
            new_category = st.text_input("New Category")
            new_due_date = st.date_input("New Due Date", value=None)
            new_due_date = new_due_date.strftime("%Y-%m-%d") if new_due_date else None
            new_priority = st.selectbox("New Priority", ["", "Low", "Medium", "High"])
            new_status = st.selectbox("New Status", ["", "Pending", "Completed"])

            if new_title: updates["title"] = new_title
            if new_description: updates["description"] = new_description
            if new_category: updates["category"] = new_category
            if new_due_date: updates["due_date"] = new_due_date
            if new_priority: updates["priority"] = new_priority
            if new_status: updates["status"] = new_status

            if st.button("💾 Save Changes"):
                if not updates:
                    st.warning("No changes made.")
                else:
                    try:
                        resp = requests.patch(f"{API_BASE}/tasks/{task_id}", json=updates)
                        if resp.status_code == 200:
                            st.success("✅ Task updated successfully!")
                            st.session_state["refresh_summary"] = True
                        else:
                            st.error("⚠️ Failed to update task.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # ----------------------------- DELETE TASK -----------------------------
    elif action == "🗑️ Delete Task":
        if not tasks:
            st.info("No tasks to delete.")
        else:
            st.markdown("### 🗑️ Delete a Task")
            task_choices = {f"{t['title']} (ID: {t['task_id']})": t["task_id"] for t in tasks}
            selected_task = st.selectbox("Select Task to Delete", list(task_choices.keys()))
            task_id = task_choices[selected_task]
            if st.button("🗑️ Confirm Delete"):
                try:
                    resp = requests.delete(f"{API_BASE}/tasks/{task_id}")
                    if resp.status_code == 200:
                        st.success(f"🧹 Task {task_id} deleted successfully!")
                        st.session_state["refresh_summary"] = True
                    else:
                        st.error("⚠️ Failed to delete task.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ====================================================
# 📊 ANALYTICS DASHBOARD PAGE
# ====================================================
elif page == "📊 Analytics":
    st.header("📊 Analytics Dashboard")

    try:
        resp = requests.get(f"{API_BASE}/tasks")
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
        st.markdown(f"Showing data from **{start_date}** to **{end_date}** — {len(df_filtered)} tasks.")

        if not df_filtered.empty and "status" in df_filtered.columns:
            total = len(df_filtered)
            completed = len(df_filtered[df_filtered["status"].str.lower() == "completed"])
            overdue = len(df_filtered[(df_filtered["due_date"] < today) & (df_filtered["status"].str.lower() != "completed")])
            recurring = len(df_filtered[df_filtered["title"].str.contains("weekly|every", case=False, na=False)])

            completion_rate = round((completed / total) * 100, 1)
            overdue_rate = round((overdue / total) * 100, 1)
            recurring_rate = round((recurring / total) * 100, 1)

            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Completion Rate", f"{completion_rate}%")
            col2.metric("⚠️ Overdue Rate", f"{overdue_rate}%")
            col3.metric("🔁 Recurring Tasks", f"{recurring_rate}%")

            st.markdown("---")
            st.subheader("📊 Task Distributions")

            # Priority pie chart
            if "priority" in df_filtered.columns:
                fig1 = px.pie(df_filtered, names="priority", title="Priority Distribution", hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)

            # Status bar chart
            fig2 = px.bar(df_filtered, x="status", color="status", title="Task Status Overview", text_auto=True)
            st.plotly_chart(fig2, use_container_width=True)

            # Time trend line chart
            if "due_date" in df_filtered.columns:
                trend = df_filtered.groupby([df_filtered["due_date"].dt.date, "status"]).size().reset_index(name="count")
                fig3 = px.line(trend, x="due_date", y="count", color="status", title="Tasks Over Time", markers=True)
                st.plotly_chart(fig3, use_container_width=True)

# ====================================================
# 🧠 AI SUMMARY SECTION
# ====================================================
st.markdown("---")
st.subheader("🧠 AI Summary")

def fetch_ai_summary():
    try:
        resp = requests.get(f"{API_BASE}/ai/summary")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"❌ Error fetching AI summary: {e}")
    return None

if "refresh_summary" not in st.session_state:
    st.session_state["refresh_summary"] = False

if st.button("✨ Generate Smart Summary"):
    st.session_state["refresh_summary"] = True

if st.session_state["refresh_summary"]:
    data = fetch_ai_summary()
    if data:
        st.success("✅ Summary updated!")
        st.markdown(data.get("summary", ""))

        stats = data.get("stats", {})
        if stats:
            col1, col2, col3 = st.columns(3)
            col1.metric("🗂️ Total", stats.get("total", 0))
            col2.metric("✅ Completed", stats.get("completed", 0))
            col3.metric("⚠️ Overdue", stats.get("overdue", 0))

    st.session_state["refresh_summary"] = False
