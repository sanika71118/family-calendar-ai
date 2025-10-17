# backend/task_manager.py
import sqlite3
from datetime import datetime, timedelta
import os, smtplib
from email.message import EmailMessage
from backend.ai_agent import predict_auto_renew

# =====================================================
# 📂 DATABASE PATH
# =====================================================
DB_PATH = "database/family_calendar.db"

# ----------------- Helper: Safe Date Parsing -----------------
def safe_parse_date(date_str):
    """Safely parse a date string (YYYY-MM-DD)."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# =====================================================
# 🧱 INITIALIZE DATABASE
# =====================================================
def init_db():
    """Create database and table if they don’t exist."""
    os.makedirs("database", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                due_date TEXT,
                duration REAL,
                priority TEXT DEFAULT 'Medium',
                reminder_days INTEGER DEFAULT 1,
                status TEXT DEFAULT 'Pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                recurring_rule TEXT,
                tags TEXT,
                user_email TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_due_date ON tasks(due_date)")
        conn.commit()
    print("✅ Database initialized successfully.")


# =====================================================
# ➕ ADD TASK
# =====================================================
def add_task(user_email, title, description="", category="", due_date=None,
             duration=None, priority="Medium", reminder_days=1,
             status="Pending", recurring_rule=None, tags=None):
    """Add a new task to the database for a specific user."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO tasks (title, description, category, due_date, duration,
                               priority, reminder_days, status,
                               recurring_rule, tags, user_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, category, due_date, duration, priority,
              reminder_days, status, recurring_rule, tags, user_email))
        conn.commit()


# =====================================================
# ✏️ UPDATE TASK
# =====================================================
def update_task(user_email, task_id, **kwargs):
    """Update a user's specific task."""
    if not kwargs:
        return
    fields = ", ".join([f"{k}=?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_email, task_id]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        q = f"UPDATE tasks SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE user_email=? AND task_id=?"
        c.execute(q, values)
        if c.rowcount == 0:
            raise ValueError("Task not found or not owned by user.")
        conn.commit()


# =====================================================
# ✅ MARK COMPLETE
# =====================================================
def mark_task_complete(user_email, task_id):
    """Mark a user's task as completed."""
    update_task(user_email, task_id, status="Completed")


# =====================================================
# ❌ DELETE TASK
# =====================================================
def delete_task(user_email, task_id):
    """Delete a user's specific task."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE user_email=? AND task_id=?", (user_email, task_id))
        if c.rowcount == 0:
            raise ValueError("Task not found or not owned by user.")
        conn.commit()


# =====================================================
# 📋 LIST TASKS
# =====================================================
def list_tasks(user_email, sort_by=None):
    """Fetch all tasks for a specific user."""
    allowed_sort = {"due_date", "priority", "category"}
    query = """
        SELECT task_id, title, description, category, due_date, priority,
               reminder_days, status
        FROM tasks
        WHERE user_email=?
    """
    if sort_by in allowed_sort:
        query += f" ORDER BY {sort_by}"

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, (user_email,)).fetchall()

    return rows


# =====================================================
# 📧 EMAIL REMINDERS
# =====================================================
def send_email_reminder(to_email, task):
    """Send email reminder for an upcoming task."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        print(f"⚠️ Email not sent for '{task['title']}' — credentials not set.")
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
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        print(f"📧 Reminder sent for '{task['title']}' to {to_email}")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")


# =====================================================
# 🔁 RECURRING SUGGESTIONS (AI)
# =====================================================
def get_recurring_suggestions(user_email):
    """Use AI to suggest recurring tasks for auto-addition."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT title, description, category, due_date, priority, reminder_days
            FROM tasks WHERE user_email=?
        """, (user_email,))
        rows = c.fetchall()

    suggestions = []
    for row in rows:
        title, description, category, due_date, priority, reminder_days = row
        parsed_due_date = safe_parse_date(due_date)
        if not parsed_due_date:
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
    return suggestions


# =====================================================
# 📊 SUMMARY STATS
# =====================================================
def get_summary_stats(user_email):
    """Return basic summary stats for the user."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN LOWER(status)='completed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(status)!='completed' AND due_date < DATE('now') THEN 1 ELSE 0 END)
            FROM tasks WHERE user_email=?
        """, (user_email,))
        total, completed, overdue = c.fetchone()

        c.execute("""
            SELECT category, COUNT(*) FROM tasks
            WHERE user_email=? GROUP BY category
        """, (user_email,))
        categories = {r[0] or "Uncategorized": r[1] for r in c.fetchall()}

    return {
        "total": total or 0,
        "completed": completed or 0,
        "overdue": overdue or 0,
        "categories": categories
    }


# =====================================================
# 🧪 TEST RUN
# =====================================================
if __name__ == "__main__":
    init_db()
    print("✅ Tables ready")
