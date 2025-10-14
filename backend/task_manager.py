import sqlite3
from tabulate import tabulate
from colorama import Fore, Style
from datetime import datetime, timedelta
from backend.ai_agent import get_effective_priority, predict_auto_renew
import smtplib
from email.message import EmailMessage
import os

# ✅ DB path defined first
DB_PATH = "database/family_calendar.db"

# ----------------- ✅ Helper: Safe Date Parsing -----------------
def safe_parse_date(date_str):
    """Safely parse a date string (YYYY-MM-DD)."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ----------------- Database Initialization -----------------
def init_db():
    """Create database and table if they don’t exist."""
    os.makedirs("database", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
        # ✅ Fast sorting by due_date
        c.execute("CREATE INDEX IF NOT EXISTS idx_due_date ON tasks(due_date)")
        conn.commit()
    print("✅ Database initialized successfully.")


# ----------------- CRUD -----------------
def add_task(title, description="", category="", due_date=None,
             duration=None, priority="Medium", reminder_days=1,
             status="Pending", recurring_rule=None, tags=None):
    """Add a new task to the database."""
    with sqlite3.connect(DB_PATH) as conn:
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
    print(f"✅ Task '{title}' added successfully!")


def update_task(task_id, **kwargs):
    """Update an existing task by ID."""
    if not kwargs:
        return
    fields = ", ".join([f"{k}=?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [task_id]
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        query = f"UPDATE tasks SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE task_id=?"
        c.execute(query, values)
        conn.commit()
    print(f"✅ Task {task_id} updated successfully!")


def mark_task_complete(task_id):
    """Mark a task as completed."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE tasks SET status='Completed', updated_at=CURRENT_TIMESTAMP WHERE task_id=?", (task_id,))
        conn.commit()
    print(f"✅ Task {task_id} marked as completed!")


def delete_task(task_id):
    """Delete a task by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
        conn.commit()
    print(f"✅ Task {task_id} deleted successfully!")


def clear_all_tasks():
    """Delete all tasks."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks")
        conn.commit()
    print("✅ All tasks cleared successfully!")


# ----------------- Email -----------------
def send_email_reminder(to_email, task):
    """Send email reminder for an upcoming task."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        print(f"⚠️ Email not sent for '{task['title']}' — EMAIL_USER or EMAIL_PASS not set.")
        return

    subject = f"Reminder: {task['title']} due {task['due_date']}"
    body = (
        f"Task: {task['title']}\n"
        f"Description: {task['description']}\n"
        f"Due Date: {task['due_date']}\n"
        f"Priority: {task['priority']}"
    )

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
    """Display all tasks in a formatted table."""
    allowed_sort = {"due_date", "priority", "category"}
    query = """
        SELECT task_id, title, description, category, due_date, priority, reminder_days, status
        FROM tasks
    """
    if sort_by in allowed_sort:
        query += f" ORDER BY {sort_by}"

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()

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

            if days_left < 0 or days_left <= 3:
                stored_priority = "High"
            elif days_left <= 7:
                stored_priority = "Medium"
            else:
                stored_priority = "Low"

        # Priority and status colors
        priority_display = (
            f"{Fore.RED}{stored_priority}{Style.RESET_ALL}" if stored_priority.lower() == "high"
            else f"{Fore.YELLOW}{stored_priority}{Style.RESET_ALL}" if stored_priority.lower() == "medium"
            else f"{Fore.CYAN}{stored_priority}{Style.RESET_ALL}"
        )

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
    print(tabulate(table, headers=headers, tablefmt="grid", stralign="center", numalign="center"))


# ----------------- Recurring Suggestions -----------------
def get_recurring_suggestions():
    """Use AI to suggest recurring tasks for auto-addition."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT title, description, category, due_date, priority, reminder_days FROM tasks")
        rows = c.fetchall()

    suggestions = []
    for row in rows:
        title, description, category, due_date, priority, reminder_days = row
        parsed_due_date = safe_parse_date(due_date)
        if not parsed_due_date:
            print(f"⚠️ Skipping task '{title}' — invalid or missing due date.")
            continue

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

    if not suggestions:
        print("\n📭 No recurring tasks detected.")
    else:
        print(f"\n🔁 {len(suggestions)} recurring tasks suggested for auto-addition.\n")

    return suggestions
