from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.task_manager import (
    add_task, update_task, mark_task_complete,
    delete_task, clear_all_tasks, view_tasks, get_recurring_suggestions
)
from backend.ai_agent import suggest_priority, extract_priority, predict_auto_renew

app = FastAPI(title="Family Calendar AI API", version="1.0")

# ----------- MODELS -----------
class Task(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    due_date: Optional[str] = None
    priority: Optional[str] = "Medium"
    reminder_days: Optional[int] = 1
    status: Optional[str] = "Pending"

# ----------- ROUTES -----------
@app.get("/")
def root():
    return {"message": "✅ Family Calendar API is running!"}

@app.post("/tasks")
def create_task(task: Task):
    add_task(**task.dict())
    return {"message": f"Task '{task.title}' added successfully!"}

@app.get("/tasks")
def get_tasks():
    view_tasks()
    return {"message": "Tasks printed to console (view CLI logs)"}

@app.patch("/tasks/{task_id}")
def update(task_id: int, updates: dict):
    update_task(task_id, **updates)
    return {"message": f"Task {task_id} updated!"}

@app.delete("/tasks/{task_id}")
def delete(task_id: int):
    delete_task(task_id)
    return {"message": f"Task {task_id} deleted!"}

@app.post("/tasks/{task_id}/complete")
def complete(task_id: int):
    mark_task_complete(task_id)
    return {"message": f"Task {task_id} marked completed!"}

@app.post("/tasks/clear")
def clear():
    clear_all_tasks()
    return {"message": "All tasks cleared."}

# ----------- AI ROUTES -----------
@app.post("/ai/priority")
def ai_priority(task: Task):
    response = suggest_priority(task.title, task.description, task.due_date)
    return {"ai_response": response, "priority": extract_priority(response)}

@app.post("/ai/recurring")
def ai_recurring(task: Task):
    result = predict_auto_renew(task.title, task.description)
    return {"auto_renew": result}

@app.get("/ai/suggestions")
def recurring_suggestions():
    suggestions = get_recurring_suggestions()
    return {"suggestions": suggestions}
