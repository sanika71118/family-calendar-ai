# backend/ai_agent.py
from datetime import datetime
from openai import OpenAI

client = OpenAI()

def suggest_priority(title, description="", due_date=None):
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
        model="gpt-4o-mini",  # or gpt-3.5-turbo if you prefer cheaper
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content.strip()
    return reply
