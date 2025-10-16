import streamlit as st
import requests
import pandas as pd
from streamlit_calendar import calendar as st_calendar
import plotly.express as px


import os, streamlit as st
API_BASE = st.secrets.get("API_BASE") or os.environ.get("API_BASE") or "http://127.0.0.1:8000"

# ----------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------
st.set_page_config(page_title="Family Calendar AI", layout="wide")
st.title("🧭 Family Calendar AI")
st.caption("Plan, track, and visualize your family’s schedule — all in one place.")

# ----------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["📅 Calendar", "📊 Analytics"])

# ====================================================
# 📅 CALENDAR PAGE
# ====================================================
if page == "📅 Calendar":

    try:
        resp = requests.get(f"{API_BASE}/tasks")
        if resp.status_code == 200:
            tasks = resp.json().get("tasks", [])
        else:
            tasks = []
    except Exception as e:
        st.error(f"⚠️ Could not connect to backend: {e}")
        tasks = []

    if not tasks:
        st.info("📭 No tasks yet. Add some below!")
    else:
        events = []
        color_map = {"High": "#e74c3c", "Medium": "#f1c40f", "Low": "#2ecc71"}

        for t in tasks:
            if t["due_date"]:
                events.append({
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
                })

        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay"
            },
            "editable": False,
            "selectable": True,
            "height": 650,
        }

        st_calendar(events=events, options=calendar_options, key="family_calendar_ui")
        st.markdown("🟢 **Low Priority** 🟡 **Medium Priority** 🔴 **High Priority**")

    # ----------------------------------------------------
    # FLOATING “+” BUTTON (scrolls to Add Task section)
    # ----------------------------------------------------
    float_btn = st.empty()
    with float_btn.container():
        st.markdown("""
        <style>
        .floating-button {
            position: fixed;
            bottom: 60px;
            right: 60px;
            background-color: #2ecc71;
            color: white;
            border-radius: 50%;
            height: 60px;
            width: 60px;
            font-size: 28px;
            text-align: center;
            line-height: 60px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            z-index: 999;
        }
        .floating-button:hover { transform: scale(1.08); }
        </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([5, 5, 1])
        with col3:
            if st.button("➕", key="addtask_btn"):
                st.session_state.active_action = "➕ Add Task"
                st.rerun()

    # ----------------------------------------------------
    # QUICK ACTIONS MENU
    # ----------------------------------------------------
    st.markdown("---")
    st.subheader("⚡ Quick Actions")

    action = st.selectbox(
        "Select Action",
        ["None", "➕ Add Task", "✏️ Update Task", "🗑️ Delete Task", "🤖 AI Tools"],
        index=0
    )

    # ---- AI Priority Suggestion ----
    if st.button("🤖 Suggest Priority", key="ai_suggest_btn"):
        try:
            resp = requests.post(
                f"{API_BASE}/ai/priority",
                json={"title": title, "description": description, "due_date": due_date},
            )
            if resp.status_code == 200:
                result = resp.json()
                st.session_state["ai_priority"] = result.get("priority", "Medium")
                st.session_state["ai_reason"] = result.get("ai_response", "")
            else:
                st.warning("⚠️ AI service returned an error.")
        except Exception as e:
            st.error(f"AI Error: {e}")

    # Display AI suggestion if present
    if "ai_priority" in st.session_state:
        st.markdown(f"**Suggested Priority:** {st.session_state['ai_priority']}")
        st.markdown(f"**AI Explanation:** {st.session_state['ai_reason']}")

    # ----------------------------- ADD TASK -----------------------------
    if action == "➕ Add Task":
        st.markdown("### <a name='addtask'></a>➕ Add New Task", unsafe_allow_html=True)

        title = st.text_input("Title")
        description = st.text_area("Description")
        category = st.text_input("Category")
        due_date = st.date_input("Due Date (optional)", value=None)
        due_date = due_date.strftime("%Y-%m-%d") if due_date else None
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        reminder_days = st.number_input("Reminder Days", min_value=0, value=1, step=1)

        if st.button("✅ Add Task"):
            try:
                data = {
                    "title": title,
                    "description": description,
                    "category": category,
                    "due_date": due_date,
                    "priority": priority,
                    "reminder_days": reminder_days
                }
                r = requests.post(f"{API_BASE}/tasks", json=data)
                if r.status_code == 200:
                    st.success(r.json().get("message", "Task added successfully!"))
                    st.toast("✅ Task added — refresh calendar to view it.")
                    st.session_state["refresh_summary"] = True   # auto-update AI Summary

                else:
                    st.error(f"⚠️ Failed to add task ({r.status_code})")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    # ----------------------------------------------------
    # UPDATE TASK
    # ----------------------------------------------------
    elif action == "✏️ Update Task":
        st.markdown("### ✏️ Update an Existing Task")
        if not tasks:
            st.info("No tasks found to update.")
        else:
            task_choices = {f"{t['title']} (ID: {t['task_id']})": t['task_id'] for t in tasks}
            selected_task = st.selectbox("Select Task", list(task_choices.keys()))
            task_id = task_choices[selected_task]

            new_title = st.text_input("New Title (optional)")
            new_description = st.text_area("New Description (optional)")
            new_category = st.text_input("New Category (optional)")
            new_due_date = st.date_input("New Due Date (optional)", value=None)
            new_due_date = new_due_date.strftime("%Y-%m-%d") if new_due_date else None
            new_priority = st.selectbox("New Priority", ["", "Low", "Medium", "High"])
            new_status = st.selectbox("New Status", ["", "Pending", "Completed"])

            updates = {}
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
                            st.toast("Task updated — refresh calendar to view changes.")
                            st.session_state["refresh_summary"] = True

                        else:
                            st.error("⚠️ Failed to update task.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # ----------------------------------------------------
    # DELETE TASK
    # ----------------------------------------------------
    elif action == "🗑️ Delete Task":
        st.markdown("### 🗑️ Delete a Task")
        if not tasks:
            st.info("No tasks to delete.")
        else:
            task_choices = {f"{t['title']} (ID: {t['task_id']})": t['task_id'] for t in tasks}
            selected_task = st.selectbox("Select Task to Delete", list(task_choices.keys()))
            task_id = task_choices[selected_task]
            if st.button("🗑️ Confirm Delete"):
                try:
                    resp = requests.delete(f"{API_BASE}/tasks/{task_id}")
                    if resp.status_code == 200:
                        st.success(f"🧹 Task {task_id} deleted successfully!")
                        st.toast("Task deleted — refresh calendar to view changes.")
                        st.session_state["refresh_summary"] = True

                    else:
                        st.error("⚠️ Failed to delete task.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # ----------------------------------------------------
    # AI TOOLS SECTION
    # ----------------------------------------------------
    elif action == "🤖 AI Tools":
        st.markdown("### 🤖 AI Suggestions")

        st.write("Generate recurring task suggestions or get AI-predicted priorities.")
        if st.button("Generate Recurring Suggestions"):
            try:
                resp = requests.get(f"{API_BASE}/ai/suggestions")
                if resp.status_code == 200:
                    data = resp.json()
                    suggestions = data.get("suggestions", [])
                    if suggestions:
                        df = pd.DataFrame(suggestions)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("✅ No recurring tasks found.")
                else:
                    st.error("⚠️ Failed to fetch AI suggestions.")
            except Exception as e:
                st.error(f"❌ Error: {e}")





# ====================================================
# 📊 ANALYTICS DASHBOARD PAGE
# ====================================================
elif page == "📊 Analytics":
    st.header("📊 Analytics Dashboard")

    # --- Fetch tasks from backend ---
    try:
        resp = requests.get(f"{API_BASE}/tasks")
        tasks = resp.json().get("tasks", [])
    except Exception as e:
        st.error(f"⚠️ Could not load tasks: {e}")
        tasks = []

    if not tasks:
        st.info("📭 No data available for analytics.")
    else:
        import plotly.express as px
        df = pd.DataFrame(tasks)
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
        today = pd.Timestamp.today().normalize()

        # ====================================================
        # 📅 DATE RANGE & PRESET FILTERS
        # ====================================================
        st.markdown("### 📆 Filter by Due Date Range")

        # Compute safe date bounds
        min_date = df["due_date"].min()
        max_date = df["due_date"].max()
        if pd.isna(min_date):
            min_date = today - pd.Timedelta(days=30)
        if pd.isna(max_date):
            max_date = today
        if min_date == max_date:
            min_date = max_date - pd.Timedelta(days=7)

        # Preset selector
        preset = st.selectbox(
            "Preset Range",
            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
            index=1,
        )

        if preset == "Last 7 days":
            default_start = today - pd.Timedelta(days=7)
            default_end = today
        elif preset == "Last 90 days":
            default_start = today - pd.Timedelta(days=90)
            default_end = today
        elif preset == "All time":
            default_start, default_end = min_date, max_date
        else:  # Last 30 days
            default_start = today - pd.Timedelta(days=30)
            default_end = today

        # Clamp defaults within bounds
        default_start = max(default_start, min_date)
        default_end = min(default_end, max_date)

        # Date picker
        start_date, end_date = st.date_input(
            "Custom date range:",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date,
        )

        # Apply filter
        mask = (df["due_date"] >= pd.to_datetime(start_date)) & (
            df["due_date"] <= pd.to_datetime(end_date)
        )
        df_filtered = df[mask].copy()

        st.markdown(
            f"Showing data from **{start_date}** to **{end_date}** — {len(df_filtered)} tasks."
        )






# ====================================================
# 📈 KPI METRICS & CHARTS SECTION 
# ====================================================

# --- Ensure due_date is datetime ---
if 'due_date' in df.columns:
    df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce')

# --- Safe filtering logic ---
if 'df' in locals() and not df.empty:
    df_filtered = df[
        (df['due_date'] >= pd.to_datetime(start_date))
        & (df['due_date'] <= pd.to_datetime(end_date))
    ]
else:
    df_filtered = pd.DataFrame()

# --- Show message if no data ---
if df_filtered.empty:
    st.warning("⚠️ No data available for the selected range.")
else:
    st.markdown("### 📊 Task Analytics")

    # --- Compute KPIs ---
    total = len(df_filtered)
    completed = len(df_filtered[df_filtered['status'].str.lower() == "completed"])
    overdue = len(df_filtered[
        (df_filtered['due_date'] < today) &
        (df_filtered['status'].str.lower() != "completed")
    ])
    recurring = len(df_filtered[
        df_filtered['title'].str.contains("weekly|every", case=False, na=False)
    ])

    completion_rate = round((completed / total) * 100, 1)
    overdue_rate = round((overdue / total) * 100, 1)
    recurring_rate = round((recurring / total) * 100, 1)

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Completion Rate", f"{completion_rate}%")
    col2.metric("⚠️ Overdue Rate", f"{overdue_rate}%")
    col3.metric("🔁 Recurring Tasks", f"{recurring_rate}%")

    st.markdown("---")

    # ====================================================
    # 📉 VISUAL CHARTS
    # ====================================================

    # Priority Distribution
    if "priority" in df_filtered.columns:
        fig1 = px.pie(
            df_filtered,
            names="priority",
            title="Priority Distribution",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Task Status Overview
    fig2 = px.bar(
        df_filtered,
        x="status",
        color="status",
        title="Task Status Overview",
        text_auto=True,
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Tasks Over Time
    if "due_date" in df_filtered.columns:
        time_trend = df_filtered.groupby(
            [df_filtered['due_date'].dt.date, 'status']
        ).size().reset_index(name='count')
        fig3 = px.line(
            time_trend,
            x="due_date",
            y="count",
            color="status",
            title="Tasks Over Time by Status",
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig3, use_container_width=True)







# -----------------------------
# 🧠 AI SUMMARY SECTION (Styled)
# -----------------------------
import streamlit as st

st.markdown("---")
st.subheader("🧠 AI Summary")

# --- Define helper to fetch summary ---
def fetch_ai_summary():
    try:
        resp = requests.get(f"{API_BASE}/ai/summary")
        if resp.status_code == 200:
            data = resp.json()
            return data
        else:
            st.error("⚠️ Failed to generate summary.")
            return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

# --- Auto-refresh trigger key (updates when tasks change) ---
if "refresh_summary" not in st.session_state:
    st.session_state["refresh_summary"] = False

# --- AI Summary button (manual trigger still available) ---
if st.button("✨ Generate Smart Summary"):
    st.session_state["refresh_summary"] = True

# --- Auto refresh if user added/updated/deleted tasks ---
# When tasks are modified, update st.session_state["refresh_summary"] = True in those sections.
if st.session_state.get("refresh_summary", False):
    data = fetch_ai_summary()
    if data:
        st.success("✅ Summary updated!")
        st.markdown(data.get("summary", ""))

        # --- Styled Stats Overview ---
        st.markdown("### 📊 Stats Overview")
        stats = data.get("stats", {})

        if stats:
            total = stats.get("total", 0)
            completed = stats.get("completed", 0)
            overdue = stats.get("overdue", 0)
            categories = stats.get("categories", {})

            col1, col2, col3 = st.columns(3)

            col1.markdown(
                f"""
                <div style='background-color:#e8f4fd;padding:15px;border-radius:10px;text-align:center;'>
                <h3>🗂️ Total</h3>
                <h2 style='color:#0078D7'>{total}</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col2.markdown(
                f"""
                <div style='background-color:#eafbea;padding:15px;border-radius:10px;text-align:center;'>
                <h3>✅ Completed</h3>
                <h2 style='color:#1E8449'>{completed}</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col3.markdown(
                f"""
                <div style='background-color:#fff3e0;padding:15px;border-radius:10px;text-align:center;'>
                <h3>⚠️ Overdue</h3>
                <h2 style='color:#E67E22'>{overdue}</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # --- Category breakdown paragraph ---
            if categories:
                category_lines = []
                for cat, summary in categories.items():
                    label = cat if cat.strip() else "Uncategorized"
                    category_lines.append(f"**{label}** — {summary}")
                category_text = " | ".join(category_lines)
                st.markdown(f"**Category breakdown:** {category_text}")

        else:
            st.info("No stats available yet.")

        # Reset refresh trigger
        st.session_state["refresh_summary"] = False


