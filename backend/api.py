from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
from backend.task_manager import (
    add_task, update_task, mark_task_complete,
    delete_task, clear_all_tasks, get_recurring_suggestions,
    init_db, DB_PATH
)
from backend.ai_agent import suggest_priority, extract_priority, predict_auto_renew

# ----------------- Initialize App -----------------
app = FastAPI(title="Family Calendar AI API", version="1.0")

# ✅ Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Initialize database at startup
@app.on_event("startup")
def startup_event():
    init_db()


# ----------------- Models -----------------
class Task(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    due_date: Optional[str] = None
    priority: Optional[str] = "Medium"
    reminder_days: Optional[int] = 1
    status: Optional[str] = "Pending"


# ----------------- Routes -----------------
@app.get("/")
def root():
    return {"message": "✅ Family Calendar API is running!"}


@app.post("/tasks")
def create_task(task: Task):
    """Create a new task."""
    try:
        add_task(**task.dict())
        return {"message": f"Task '{task.title}' added successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
def get_tasks(sort_by: Optional[str] = None):
    """
    Fetch all tasks from SQLite database.
    Optionally sorted by due_date, priority, or category.
    Returns JSON data for Streamlit UI.
    """
    allowed_sort = {"due_date", "priority", "category"}
    base_query = """
        SELECT task_id, title, description, category, due_date, priority, reminder_days, status
        FROM tasks
    """

    # Add proper sorting
    if sort_by == "due_date":
        query = base_query + " ORDER BY CASE WHEN due_date IS NULL OR due_date='' THEN 1 ELSE 0 END, date(due_date)"
    elif sort_by == "priority":
        query = base_query + """
            ORDER BY 
                CASE 
                    WHEN lower(priority) = 'high' THEN 3
                    WHEN lower(priority) = 'medium' THEN 2
                    WHEN lower(priority) = 'low' THEN 1
                    ELSE 0
                END DESC
        """
    elif sort_by == "category":
        query = base_query + " ORDER BY lower(category)"
    else:
        query = base_query

    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute(query)
            rows = c.fetchall()

        tasks = [
            {
                "task_id": row[0],
                "title": row[1],
                "description": row[2],
                "category": row[3],
                "due_date": row[4],
                "priority": (row[5].title() if isinstance(row[5], str) else row[5]),
                "reminder_days": row[6],
                "status": row[7],
            }
            for row in rows
        ]
        return {"tasks": tasks}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.patch("/tasks/{task_id}")
def update(task_id: int, updates: dict):
    """Update a task by ID."""
    try:
        update_task(task_id, **updates)
        return {"message": f"Task {task_id} updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tasks/{task_id}")
def delete(task_id: int):
    """Delete a task by ID."""
    try:
        delete_task(task_id)
        return {"message": f"Task {task_id} deleted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/{task_id}/complete")
def complete(task_id: int):
    """Mark a task as completed."""
    try:
        mark_task_complete(task_id)
        return {"message": f"Task {task_id} marked completed!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/clear")
def clear():
    """Delete all tasks."""
    try:
        clear_all_tasks()
        return {"message": "All tasks cleared successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- AI Routes -----------------
@app.post("/ai/priority")
def ai_priority(task: Task):
    """Return AI-generated priority suggestion for a task."""
    try:
        response = suggest_priority(task.title, task.description, task.due_date)
        return {
            "ai_response": response,
            "priority": extract_priority(response)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/recurring")
def ai_recurring(task: Task):
    """Predict if a single task is recurring."""
    try:
        result = predict_auto_renew(task.title, task.description)
        return {"auto_renew": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/suggestions")
def recurring_suggestions():
    """Generate recurring task suggestions from the database."""
    try:
        suggestions = get_recurring_suggestions()
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
