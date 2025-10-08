from backend.task_manager import (
    add_task, view_tasks, mark_task_complete,
    update_task, delete_task, clear_all_tasks, get_recurring_suggestions,
    init_db  # 👈 add this
)

from backend.ai_agent import suggest_priority, extract_priority

def main():
    init_db()
    user_email = input("Enter your email for reminders (optional): ").strip() or None

    while True:
        print("\n📅 Family Calendar CLI")
        print("1. Add Task")
        print("2. View Tasks")
        print("3. Mark Task Complete")
        print("4. Update Task")
        print("5. Delete Task")
        print("6. Clear All Tasks")
        print("0. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            title = input("Task Title: ").strip()
            description = input("Description (optional): ").strip()
            category = input("Category (optional): ").strip()
            due_date = input("Due Date (YYYY-MM-DD) (optional): ").strip() or None
            reminder_days = input("Reminder Days (default 1): ").strip() or 1
            reminder_days = int(reminder_days)

            ai_response = suggest_priority(title, description, due_date)
            base_priority = extract_priority(ai_response)
            print(f"\n🤖 AI Suggestion:\n{ai_response}\n")

            user_priority = input("Priority [Low/Medium/High] (press Enter to accept AI suggestion): ").strip().capitalize()
            while user_priority not in {"", "Low", "Medium", "High"}:
                user_priority = input("Invalid choice. Enter Low, Medium, High, or press Enter: ").strip().capitalize()
            if user_priority:
                base_priority = user_priority

            add_task(title, description, category, due_date,
                     priority=base_priority, reminder_days=reminder_days)

        elif choice == "2":
            sort_prompt = input("Sort by (none/due_date/priority/category): ").strip().lower()
            sort_by = sort_prompt if sort_prompt in {"due_date", "priority", "category"} else None
            view_tasks(sort_by=sort_by, user_email=user_email)

            auto_add = input("\nDo you want to auto-add AI-predicted recurring tasks? (y/n): ").strip().lower()
            if auto_add == "y":
                suggestions = get_recurring_suggestions()
                if not suggestions:
                    print("📭 No recurring tasks detected.")
                else:
                    for task in suggestions:
                        add_task(
                            task['title'],
                            task['description'],
                            task['category'],
                            task['due_date'],
                            priority=task['priority'],
                            reminder_days=task['reminder_days']
                        )
                    print(f"✅ {len(suggestions)} recurring tasks auto-added.")

        elif choice == "3":
            task_id = input("Task ID to mark complete: ").strip()
            if task_id.isdigit():
                mark_task_complete(int(task_id))

        elif choice == "4":
            task_id = input("Task ID to update: ").strip()
            field = input("Field to update (title/description/category/due_date/priority/status): ").strip()
            value = input("New value: ").strip()
            if task_id.isdigit():
                update_task(int(task_id), **{field: value})

        elif choice == "5":
            task_id = input("Enter the Task ID to delete: ").strip()
            if task_id.isdigit():
                delete_task(int(task_id))

        elif choice == "6":
            confirm = input("Are you sure? This will delete ALL tasks! (y/n): ").strip().lower()
            if confirm == "y":
                clear_all_tasks()

        elif choice == "0":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Try again.")

if __name__ == "__main__":
    main()
