import sqlite3
from tabulate import tabulate
from datetime import datetime, timedelta
from backend.ai_agent import get_effective_priority, predict_auto_renew
import smtplib
from email.message import EmailMessage
import os

DB_PATH = "database/family_calendar.db"

# ----------------- CRUD -----------------
def add_task(title, description="", category="", due_date=None,
             duration=None, priority="Medium", reminder_days=1,
             status="Pending", recurring_rule=None, tags=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO tasks (title, description, category, due_date,
                           duration, priority, reminder_days, status,
                           recurring_rule, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, category, due_date,
          duration, priority, reminder_days, status,
          recurring_rule, tags))
    conn.commit()
    conn.close()
    print(f"✅ Task '{title}' added successfully!")

def update_task(task_id, **kwargs):
    if not kwargs:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fields = ", ".join([f"{k}=?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(task_id)
    query = f"UPDATE tasks SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE task_id=?"
    c.execute(query, values)
    conn.commit()
    conn.close()
    print(f"✅ Task {task_id} updated successfully!")

def mark_task_complete(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status='Completed', updated_at=CURRENT_TIMESTAMP WHERE task_id=?", (task_id,))
    conn.commit()
    conn.close()
    print(f"✅ Task {task_id} marked as completed!")

def delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
    conn.commit()
    conn.close()
    print(f"✅ Task {task_id} deleted successfully!")

def clear_all_tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    print("✅ All tasks cleared successfully!")

# ----------------- Email -----------------
def send_email_reminder(to_email, task):
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        print(f"⚠️ Email not sent for '{task['title']}' — EMAIL_USER or EMAIL_PASS not set.")
        return

    subject = f"Reminder: {task['title']} due {task['due_date']}"
    body = f"Task: {task['title']}\nDescription: {task['description']}\nDue Date: {task['due_date']}\nPriority: {task['priority']}"

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = email_user
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        print(f"📧 Reminder sent for task '{task['title']}'")
    except Exception as e:
        print(f"⚠️ Failed to send email for '{task['title']}': {e}")


# ----------------- View Tasks -----------------
import textwrap

def view_tasks(sort_by=None, user_email=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    allowed_sort = {"due_date", "priority", "category"}
    query = "SELECT task_id, title, description, category, due_date, priority, reminder_days, status FROM tasks"
    if sort_by in allowed_sort:
        query += f" ORDER BY {sort_by}"

    c.execute(query)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("\n📭 No tasks found.\n")
        return

    table = []
    for row in rows:
        task_id, title, description, category, due_date, stored_priority, reminder_days, status = row
        task_obj = {
            "title": title,
            "description": description or "",
            "category": category or "",
            "due_date": due_date,
            "priority": stored_priority,
            "reminder_days": reminder_days or 1,
            "status": status or "Pending"
        }

        effective = get_effective_priority(task_obj)
        effective_priority = effective["priority"]
        priority_shifted = "Yes" if stored_priority.lower() == "low" and effective_priority == "High" else "No"
        auto_renew = predict_auto_renew(title, description)

        # Wrap text to max width per column
        title_wrapped = "\n".join(textwrap.wrap(title, 20))
        category_wrapped = "\n".join(textwrap.wrap(category, 12))

        table.append([
            task_id,
            title_wrapped,
            due_date or "N/A",
            stored_priority,
            effective_priority,
            priority_shifted,
            status,
            category_wrapped,
            auto_renew
        ])

    headers = ["ID", "Title", "Due Date", "Stored Priority", "Effective Priority",
               "Priority Shifted", "Status", "Category", "Auto-Renew"]

    print("\n📋 Current Tasks:")
    print(tabulate(table, headers, tablefmt="fancy_grid", stralign="center"))

# ----------------- Recurring Suggestions -----------------
def get_recurring_suggestions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title, description, category, due_date, priority, reminder_days FROM tasks")
    rows = c.fetchall()
    conn.close()

    suggestions = []
    for row in rows:
        title, description, category, due_date, priority, reminder_days = row
        if predict_auto_renew(title, description) == "Yes":
            next_due_date = (datetime.strptime(due_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            suggestions.append({
                "title": title,
                "description": description,
                "category": category,
                "due_date": next_due_date,
                "priority": priority,
                "reminder_days": reminder_days
            })
    return suggestions
