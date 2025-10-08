import sqlite3
from tabulate import tabulate
from colorama import Fore, Style
from datetime import datetime, timedelta
from backend.ai_agent import get_effective_priority, predict_auto_renew
import smtplib
from email.message import EmailMessage
import os

DB_PATH = "database/family_calendar.db"

# ----------------- ✅ Helper: Safe Date Parsing -----------------
def safe_parse_date(date_str):
    """
    Safely parse a date string in YYYY-MM-DD format.
    Returns a datetime.date object or None if invalid.
    Prevents crashes if user enters wrong format like 10/25/2025 or 25-10-2025.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None



# ----------------- Database Initialization -----------------
def init_db():
    """
    Creates the database and tasks table if they don't already exist.
    Ensures the app can run on a clean system without setup scripts.
    """
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            due_date TEXT,
            duration REAL,
            priority TEXT,
            reminder_days INTEGER,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            recurring_rule TEXT,
            tags TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")

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
    return  # ⚠️ Temporary return for debugging (remove if needed)

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
def view_tasks(sort_by=None, user_email=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    allowed_sort = {"due_date", "priority", "category"}
    query = """
        SELECT task_id, title, description, category, due_date, priority, reminder_days, status
        FROM tasks
    """
    if sort_by in allowed_sort:
        query += f" ORDER BY {sort_by}"

    c.execute(query)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("\n📭 No tasks found.\n")
        return

    table = []
    today = datetime.now().date()

    for row in rows:
        task_id, title, description, category, due_date, stored_priority, reminder_days, status = row
        due_date_display = due_date or "N/A"
        notes = ""
        days_left_text = "N/A"

        # ✅ Use safe date parser instead of direct strptime
        task_due_date = safe_parse_date(due_date)

        if not task_due_date:
            days_left_text = f"{Fore.RED}Invalid Date{Style.RESET_ALL}"
            stored_priority = "Low"
            notes = f"{Fore.RED}Invalid date format{Style.RESET_ALL}"
        else:
            days_left = (task_due_date - today).days

            if days_left < 0:
                notes = f"{Fore.RED}OVERDUE{Style.RESET_ALL}"
                days_left_text = f"{Fore.RED}Overdue by {abs(days_left)}d{Style.RESET_ALL}"
            elif days_left == 0:
                days_left_text = f"{Fore.RED}Today{Style.RESET_ALL}"
            elif days_left == 1:
                days_left_text = f"{Fore.YELLOW}Tomorrow{Style.RESET_ALL}"
            else:
                days_left_text = f"In {days_left} days"

            # Adjust priority based on how far away it is
            if days_left < 0 or days_left <= 3:
                stored_priority = "High"
            elif days_left <= 7:
                stored_priority = "Medium"
            else:
                stored_priority = "Low"

        # Priority color
        priority_display = (
            f"{Fore.RED}{stored_priority}{Style.RESET_ALL}" if stored_priority.lower() == "high"
            else f"{Fore.YELLOW}{stored_priority}{Style.RESET_ALL}" if stored_priority.lower() == "medium"
            else f"{Fore.CYAN}{stored_priority}{Style.RESET_ALL}"
        )

        # Status color
        status_display = (
            f"{Fore.GREEN}{status}{Style.RESET_ALL}" if status.lower() == "completed"
            else f"{Fore.YELLOW}{status}{Style.RESET_ALL}"
        )

        table.append([
            task_id,
            title.title(),
            due_date_display,
            days_left_text,
            priority_display,
            status_display,
            category.title() if category else "",
            notes
        ])

    headers = ["ID", "Title", "Due Date", "Days Left", "Priority", "Status", "Category", "Notes"]

    print("\n📋 Current Tasks:\n")
    print(tabulate(
        table,
        headers=headers,
        tablefmt="grid",
        stralign="center",
        numalign="center"
    ))


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

        # ✅ Safely parse date instead of direct strptime
        parsed_due_date = safe_parse_date(due_date)
        if not parsed_due_date:
            # Skip invalid or empty dates (prevents crash)
            print(f"⚠️ Skipping task '{title}' — invalid or missing due date.")
            continue

        # ✅ Use AI + safe logic for auto-renew detection
        if predict_auto_renew(title, description) == "Yes":
            next_due_date = (parsed_due_date + timedelta(days=7)).strftime("%Y-%m-%d")
            suggestions.append({
                "title": title,
                "description": description,
                "category": category,
                "due_date": next_due_date,
                "priority": priority,
                "reminder_days": reminder_days
            })

    # ✅ Summary
    if not suggestions:
        print("\n📭 No recurring tasks detected.")
    else:
        print(f"\n🔁 {len(suggestions)} recurring tasks suggested for auto-addition.\n")

    return suggestions
