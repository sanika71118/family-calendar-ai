import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

st.title("🧭 Family Calendar AI Dashboard")

# ---- Add Task ----
st.header("➕ Add Task")
title = st.text_input("Title")
description = st.text_area("Description")
category = st.text_input("Category")
due_date = st.date_input("Due Date (optional)", value=None)
if due_date:
    due_date = due_date.strftime("%Y-%m-%d")

if st.button("Suggest Priority (AI)"):
    resp = requests.post(f"{API_BASE}/ai/priority",
                         json={"title": title, "description": description, "due_date": due_date})
    st.json(resp.json())

if st.button("Add Task"):
    data = {
        "title": title, "description": description, "category": category,
        "due_date": due_date, "priority": "Medium", "reminder_days": 1
    }
    r = requests.post(f"{API_BASE}/tasks", json=data)
    st.success(r.json()["message"])

# ---- View Tasks ----
st.header("📋 Current Tasks")
if st.button("Refresh Tasks"):
    r = requests.get(f"{API_BASE}/tasks")
    st.info("Tasks printed in console (next: connect a table view)")



# ---- Current Tasks ----
st.subheader("🗒️ Current Tasks")

try:
    resp = requests.get(f"{API_BASE}/tasks")
    if resp.status_code == 200:
        tasks = resp.json().get("tasks", [])
        if tasks:
            df = pd.DataFrame(tasks)
            df["priority"] = df["priority"].apply(
                lambda p: f"🔴 {p}" if p == "High" else ("🟡 Medium" if p == "Medium" else "🔵 Low")
            )
            df["status"] = df["status"].apply(
                lambda s: f"✅ {s}" if s.lower() == "completed" else f"⏳ {s}"
            )
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("📭 No tasks found.")
    else:
        st.error("⚠️ Could not fetch tasks from backend.")
except Exception as e:
    st.error(f"❌ Error: {e}")

# Manual refresh button (optional)
if st.button("🔄 Refresh Tasks", key="refresh_tasks_button"):
    st.rerun()


# ---- Manage Tasks ----


st.markdown("---")
st.subheader("⚙️ Manage Tasks")

action = st.selectbox("Choose action", ["Update Task", "Delete Task"])
task_id = st.number_input("Task ID", min_value=1, step=1, key="task_id_input")

if action == "Update Task":
    field = st.text_input("Field to update (title/description/category/due_date/priority/status)", key="update_field")
    value = st.text_input("New value", key="update_value")
    if st.button("Update Task", key="update_button"):
        resp = requests.patch(f"{API_BASE}/tasks/{task_id}", json={field: value})
        if resp.status_code == 200:
            st.success("✅ Task updated successfully!")
        else:
            st.error("⚠️ Failed to update task.")

elif action == "Delete Task":
    if st.button("Delete Task", key="delete_button"):
        resp = requests.delete(f"{API_BASE}/tasks/{task_id}")
        if resp.status_code == 200:
            st.success("🗑️ Task deleted successfully!")
        else:
            st.error("⚠️ Failed to delete task.")




# ---- AI Recurring Task Suggestions ----
st.subheader("🔁 AI Recurring Task Suggestions")

if st.button("Generate Recurring Suggestions"):
    try:
        resp = requests.get(f"{API_BASE}/ai/recurring")
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data.get("suggestions", [])
            if suggestions:
                # Convert to DataFrame for a clean table view
                df = pd.DataFrame(suggestions)
                df["priority"] = df["priority"].apply(
                    lambda p: f"🔴 {p}" if p == "High" else ("🟡 Medium" if p == "Medium" else "🔵 Low")
                )
                st.dataframe(df, use_container_width=True)
            else:
                st.info("✅ No recurring tasks found.")
        else:
            st.error("⚠️ Failed to fetch recurring suggestions.")
    except Exception as e:
        st.error(f"❌ Error: {e}")
