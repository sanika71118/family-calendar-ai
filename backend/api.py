# backend/api.py
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, pandas as pd, os
from datetime import datetime
from openai import OpenAI

from backend.task_manager import (
    add_task, update_task, mark_task_complete,
    delete_task, get_recurring_suggestions,
    get_summary_stats, init_db, DB_PATH
)
from backend.ai_agent import suggest_priority, extract_priority, predict_auto_renew

# Initialize OpenAI
client = OpenAI()

# =====================================================
# 🚀 Initialize FastAPI App
# =====================================================
app = FastAPI(title="Family Calendar AI API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    init_user_db()


# =====================================================
# 📋 Data Models
# =====================================================
class Task(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    due_date: Optional[str] = None
    priority: Optional[str] = "Medium"
    reminder_days: Optional[int] = 1
    status: Optional[str] = "Pending"


class User(BaseModel):
    email: str


# =====================================================
# 🧑‍💻 Auth (very simple email-based)
# =====================================================
USERS_DB = "database/users.db"

def init_user_db():
    """Create users table if not exists"""
    os.makedirs("database", exist_ok=True)
    with sqlite3.connect(USERS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@app.post("/auth/register")
def register_user(user: User):
    """Register a new user by email."""
    try:
        with sqlite3.connect(USERS_DB) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (user.email,))
            conn.commit()
        return {"message": f"✅ Registered {user.email} successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/login")
def login_user(user: User):
    """Login endpoint — simply validates user exists."""
    try:
        with sqlite3.connect(USERS_DB) as conn:
            c = conn.cursor()
            c.execute("SELECT email FROM users WHERE email=?", (user.email,))
            found = c.fetchone()
        if found:
            return {"access_token": user.email, "message": "Login successful"}
        else:
            raise HTTPException(status_code=401, detail="User not found. Please register first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Helper: Inject user_email via Header
# =====================================================
def get_user_email(x_user_email: str = Header(...)):
    """Extracts user email from headers."""
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Missing user email in header.")
    return x_user_email.strip().lower()


# =====================================================
# ➕ Create Task
# =====================================================
@app.post("/tasks")
def create_task(task: Task, user_email: str = Depends(get_user_email)):
    try:
        add_task(user_email=user_email, **task.dict())
        return {"message": f"Task '{task.title}' added for {user_email}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 📦 Get Tasks (Calendar Display)
# =====================================================
@app.get("/tasks")
def get_tasks(user_email: str = Depends(get_user_email)):
    """Fetch tasks belonging to a single user (for calendar display)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT task_id, title, description, category, due_date,
                       priority, reminder_days, status
                FROM tasks
                WHERE user_email=?
                ORDER BY due_date
            """, (user_email,))
            rows = c.fetchall()

        tasks = [
            {
                "task_id": r[0],
                "title": r[1],
                "description": r[2],
                "category": r[3],
                "due_date": r[4],
                "priority": r[5],
                "reminder_days": r[6],
                "status": r[7]
            }
            for r in rows
        ]
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")


# =====================================================
# ✏️ Update Task
# =====================================================
@app.patch("/tasks/{task_id}")
def update_task_api(task_id: int, updates: dict, user_email: str = Depends(get_user_email)):
    try:
        update_task(user_email, task_id, **updates)
        return {"message": f"✅ Task {task_id} updated for {user_email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🗑️ Delete Task
# =====================================================
@app.delete("/tasks/{task_id}")
def delete_task_api(task_id: int, user_email: str = Depends(get_user_email)):
    try:
        delete_task(user_email, task_id)
        return {"message": f"🗑️ Task {task_id} deleted for {user_email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ✅ Complete Task
# =====================================================
@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, user_email: str = Depends(get_user_email)):
    try:
        mark_task_complete(user_email, task_id)
        return {"message": f"✅ Task {task_id} marked completed for {user_email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🤖 AI Priority Suggestion
# =====================================================
@app.post("/ai/priority")
def ai_priority(task: Task):
    try:
        response = suggest_priority(task.title, task.description, task.due_date)
        return {"ai_response": response, "priority": extract_priority(response)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🔁 AI Recurring Suggestion
# =====================================================
@app.get("/ai/suggestions")
def ai_recurring(user_email: str = Depends(get_user_email)):
    try:
        suggestions = get_recurring_suggestions(user_email)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🧠 AI Summary
# =====================================================
@app.get("/ai/summary")
def ai_summary(user_email: str = Depends(get_user_email)):
    """Generate a natural-language summary and structured stats for one user."""
    try:
        stats = get_summary_stats(user_email)

        prompt = f"""
You are a warm productivity coach summarizing this user's family tasks.

Stats:
Total: {stats['total']}, Completed: {stats['completed']}, Overdue: {stats['overdue']}.
Categories: {stats['categories']}

Write a friendly, encouraging 3–5 sentence summary that:
- Mentions progress and overdue items
- Highlights strong categories
- Ends with motivation.
"""

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()

        return {"summary": summary, "stats": stats}
    except Exception as e:
        return {"summary": f"⚠️ Error: {e}", "stats": {}}


# =====================================================
# 🧩 Root
# =====================================================
@app.get("/")
def root():
    return {"message": "✅ Family Calendar AI API v2 running successfully!"}
