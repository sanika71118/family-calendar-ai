from fastapi import FastAPI
from backend.task_manager import add_task, view_tasks, get_recurring_suggestions, init_db

app = FastAPI()
init_db()

@app.get("/")
def root():
    return {"message": "Family Calendar API is running!"}
