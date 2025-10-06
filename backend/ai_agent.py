import os
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# Load OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def suggest_priority(title, description="", due_date=None):
    """
    Returns AI suggestion string with Priority + Reason.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    prompt = f"""
You are an assistant that assigns task priorities (High, Medium, Low).

Today's date: {today}
Task Title: {title}
Description: {description}
Due Date: {due_date}

Rules:
- If due date is within 2 days → High priority.
- If important keywords (doctor, exam, rent, bill, surgery, project) → High.
- If due date is within 7 days → Medium.
- Otherwise → Low.

Respond with:
- Priority: <High/Medium/Low>
- Reason: <short explanation>
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content.strip()
    return reply

def extract_priority(ai_response):
    """
    Extract only High/Medium/Low from AI response.
    """
    try:
        return ai_response.split("\n")[0].replace("Priority:", "").strip()
    except:
        return "Medium"  # fallback

def get_effective_priority(task):
    """
    Dynamically calculate effective priority (AI + reminders + keywords).
    """
    title = task.get("title", "").lower()
    description = task.get("description", "").lower()
    category = task.get("category", "").lower()
    due_date_str = task.get("due_date", None)
    reminder_days = task.get("reminder_days", 1)

    priority = "Low"
    reason = []

    # Due date check
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            today = datetime.now()
            days_left = (due_date - today).days

            if days_left <= 2:
                priority = "High"
                reason.append(f"due in {days_left} days")
            elif days_left <= 7:
                priority = "Medium"
                reason.append(f"due in {days_left} days")
            else:
                reason.append(f"due in {days_left} days")

            # Reminder check
            reminder_date = due_date - timedelta(days=reminder_days)
            if today >= reminder_date and priority != "High":
                priority = "High"
                reason.append(f"reminder triggered (reminder_days={reminder_days})")
        except ValueError:
            reason.append("invalid due date format")

    # Urgent keywords
    urgent_keywords = ["doctor", "appointment", "exam", "surgery", "meeting", "interview", "deadline", "project"]
    for kw in urgent_keywords:
        if kw in title or kw in description or kw in category:
            priority = "High"
            reason.append(f"contains urgent keyword: {kw}")
            break

    return {"priority": priority, "reason": ", ".join(reason) if reason else "no strong signals"}

def predict_auto_renew(title, description=""):
    """
    Predict if a task repeats weekly and should auto-renew.
    Returns 'Yes' or 'No'.
    """
    prompt = f"""
You are an assistant that detects recurring tasks.
Task Title: {title}
Description: {description}
Does this task repeat weekly or should it auto-add? Respond 'Yes' or 'No'.
"""
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = response.choices[0].message.content.strip().lower()
    return "Yes" if "yes" in reply else "No"
