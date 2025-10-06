#%%
import sqlite3

# Connect to (or create) database
conn = sqlite3.connect("family_calendar.db")
c = conn.cursor()

# Create tasks table
c.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    due_date TEXT,
    duration REAL,
    priority TEXT,
    reminder_days INTEGER,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    recurring_rule TEXT,
    tags TEXT
)
''')

conn.commit()
conn.close()
print("Database and tasks table created successfully!")

# %%
