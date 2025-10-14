import streamlit as st
import requests
import pandas as pd
from streamlit_calendar import calendar as st_calendar

API_BASE = "http://127.0.0.1:8000"

# ----------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------
st.set_page_config(page_title="Family Calendar AI", layout="wide")
st.title("🧭 Family Calendar AI")
st.caption("Plan, track, and visualize your family’s schedule — all in one place.")

# ----------------------------------------------------
# CALENDAR VIEW (Main Section)
# ----------------------------------------------------
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
    st.markdown(
        "🟢 **Low Priority** 🟡 **Medium Priority** 🔴 **High Priority**"
    )

# ----------------------------------------------------
# FLOATING “+” BUTTON (scrolls to Add Task section)
# ----------------------------------------------------
# ✅ TRUE FLOATING ADD BUTTON — NO JAVASCRIPT NEEDED
import streamlit as st

# create empty container at page top for the button
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

    col1, col2, col3 = st.columns([5,5,1])
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
