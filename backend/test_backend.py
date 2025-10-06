from backend.task_manager import add_task, view_tasks, mark_task_complete, update_task, delete_task, clear_all_tasks

# Add tasks
add_task(title="Science Project", description="Build volcano model", due_date="2025-10-10", priority="High")
add_task(title="Grocery Shopping", description="Buy fruits and milk", due_date="2025-10-02", priority="Low")

# View all tasks
view_tasks()

# Mark first task complete
mark_task_complete(1)

# Update second task
update_task(2, title="Weekly Grocery Shopping", priority="Medium")

# Delete first task
delete_task(1)

# View all tasks again
view_tasks()
# Clear all tasks
clear_all_tasks()

# View tasks after clearing
view_tasks()
