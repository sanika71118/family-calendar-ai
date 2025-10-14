import os
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# ----------------- API Initialization -----------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file. Please add it before running.")

client = OpenAI(api_key=api_key)


# ----------------- Helper: Safe Date Parsing -----------------
def safe_parse_date(date_str):
    """Safely parse a date string (YYYY-MM-DD) and return datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# ----------------- AI Functions -----------------
def suggest_priority(title, description="", due_date=None):
    """
    Use OpenAI to suggest a priority level (High / Medium / Low)
    based on task content and due date.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    prompt = f"""
You are an assistant that assigns task priorities: High, Medium, or Low.

Today's date: {today}
Task Title: {title}
Description: {description}
Due Date: {due_date}

Rules:
- If due date is within 2 days → High priority.
- If due date is within 7 days → Medium priority.
- If keywords like doctor, exam, rent, bill, surgery, project, meeting, deadline appear → High priority.
- Otherwise → Low priority.

Respond concisely with:
Priority: <High/Medium/Low>
Reason: <short explanation>
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        # 🔁 Smart local fallback (handles "tomorrow" correctly)
        try:
            today_dt = datetime.today()
            if due_date:
                due_dt = datetime.strptime(due_date, "%Y-%m-%d")
                days_left = (due_dt - today_dt).days
                if days_left <= 2:
                    return "Priority: High\nReason: due in ≤2 days (local fallback)."
                elif days_left <= 7:
                    return "Priority: Medium\nReason: due in ≤7 days (local fallback)."
            # keyword fallback
            text = f"{title} {description}".lower()
            if any(k in text for k in ["doctor", "exam", "surgery", "rent", "bill", "deadline", "project", "meeting"]):
                return "Priority: High\nReason: urgent keyword (local fallback)."
            return "Priority: Low\nReason: no urgency signals (local fallback)."
        except Exception:
            return "Priority: Medium\nReason: Default fallback (error during generation)."


def extract_priority(ai_response):
    """Extract only the priority level (High/Medium/Low) from AI response."""
    try:
        line = ai_response.split("\n")[0].replace("Priority:", "").strip()
        if line in {"High", "Medium", "Low"}:
            return line
        return "Medium"
    except Exception:
        return "Medium"


# ----------------- Priority Evaluation -----------------
def get_effective_priority(task):
    """
    Dynamically compute effective priority using due date, reminders, and keywords.
    Safe fallback if AI is unavailable.
    """
    title = task.get("title", "").lower()
    description = task.get("description", "").lower()
    category = task.get("category", "").lower()
    due_date_str = task.get("due_date")
    reminder_days = task.get("reminder_days", 1)

    priority = "Low"
    reason = []

    if due_date_str:
        due_date = safe_parse_date(due_date_str)
        if due_date:
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

            # Reminder effect
            reminder_date = due_date - timedelta(days=reminder_days)
            if today >= reminder_date and priority != "High":
                priority = "High"
                reason.append(f"reminder triggered ({reminder_days}d before)")
        else:
            reason.append("invalid or missing due date")

    # Keyword check
    urgent_keywords = [
        "doctor", "appointment", "exam", "surgery", "meeting",
        "interview", "deadline", "project", "bill", "payment"
    ]
    for kw in urgent_keywords:
        if kw in title or kw in description or kw in category:
            priority = "High"
            reason.append(f"contains urgent keyword: {kw}")
            break

    return {
        "priority": priority,
        "reason": ", ".join(reason) if reason else "no strong signals"
    }


# ----------------- Auto-Renew Prediction -----------------
def predict_auto_renew(title, description=""):
    """
    Predict if a task repeats weekly and should auto-renew.
    Returns 'Yes' or 'No'.
    """
    prompt = f"""
You are an assistant that determines if a task repeats weekly.
If the task seems like a recurring household, work, or school task, reply 'Yes'.
Otherwise reply 'No'.

Task Title: {title}
Description: {description}

Answer with only 'Yes' or 'No'.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
    except Exception:
        # ✅ Fallback to gpt-4o-mini if gpt-5-mini not available
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

    try:
        reply = response.choices[0].message.content.strip().lower()
        return "Yes" if "yes" in reply else "No"
    except Exception as e:
        print(f"⚠️ Auto-renew AI check failed: {e}")
        return "No"
